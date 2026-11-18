"""Run store + stage runner against a fake provider (python scripts that print gate lines)."""
import json
import sys

import pytest

from runstudio import runner, store

SCRIPTS = {
    "ok.py": "print('TOOLS: missing/bad=0')",
    "create.py": ("import sys, pathlib\n"
                  "d = pathlib.Path(sys.argv[1]); (d / 'out').mkdir(parents=True, exist_ok=True)\n"
                  "(d / 'out' / 'app.elf').write_bytes(b'image-1')\n"
                  "print('Created', d)"),
    "nogate.py": "print('all good, trust me')",
    "flash.py": ("import sys\n"
                 "if '--yes' not in sys.argv:\n"
                 "    print('ACTION: APPROVE flash app.elf to the board'); sys.exit(10)\n"
                 "print('FLASH: PASS')"),
    "connect.py": "import sys\nprint('ACTION: CONNECT plug the board'); sys.exit(10)",
    "fail.py": "import sys\nprint('BUILD: FAIL'); sys.exit(1)",
    "warn.py": "import sys\nprint('RESULT: WARNINGS'); sys.exit(2)",
    "slow.py": "import time\nprint('start', flush=True)\ntime.sleep(60)\nprint('BUILD: PASS')",
}


def provider(tmp_path, monkeypatch, stages):
    repo = tmp_path / "repo"
    scripts = repo / "skills" / "fake-skill" / "scripts"
    scripts.mkdir(parents=True)
    for name, body in SCRIPTS.items():
        (scripts / name).write_text(body, encoding="utf-8")
    manifests = tmp_path / "providers"
    manifests.mkdir()
    (manifests / "fake.json").write_text(json.dumps({
        "schema": 1, "id": "fake", "label": "Fake", "repo": str(repo),
        "targets": [{"board": "fake-board", "skill": "fake-skill", "templates": ["blink"]}], "stages": stages}), encoding="utf-8")
    monkeypatch.setenv("FWLC_PROVIDERS_DIR", str(manifests))
    monkeypatch.setenv("FWLC_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FW_WS", str(tmp_path / "ws"))
    return store.new_run("fake", "fake-board", "blink", "demo")


def st(stage_id, script, gate, **extra):
    return {"id": stage_id, "label": stage_id, "argv": ["{python}", "{scripts}/" + script, "{app_dir}"], "gate": gate, **extra}


def states(run_id):
    return [s["state"] for s in store.load_run(run_id)["stages"]]


def test_chain_passes_and_records_evidence_logs_and_artifacts(tmp_path, monkeypatch):
    run = provider(tmp_path, monkeypatch, [
        st("tools", "ok.py", "missing/bad=0"),
        st("create", "create.py", "Created ", evidence="created", artifacts=["out/*.elf"])])
    assert runner.serve(run["run_id"]) == 0
    run = store.load_run(run["run_id"])
    assert states(run["run_id"]) == ["passed", "passed"]
    assert run["stages"][0]["gate"] == "TOOLS: missing/bad=0"
    assert store.evidence(run) == "created" and store.summary(run) == "done"
    assert (store.run_dir(run["run_id"]) / "logs" / run["stages"][1]["log"]).read_text(encoding="utf-8").count("Created") == 1
    rows = store.artifacts(run)
    assert [r["file"] for r in rows] == ["out/app.elf"] and rows[0]["stage"] == "create" and len(rows[0]["sha256"]) == 64
    assert [e["event"] for e in store.events(run["run_id"])].count("stage_ended") == 2


def test_exit_zero_without_gate_line_is_not_a_pass(tmp_path, monkeypatch):
    run = provider(tmp_path, monkeypatch, [st("build", "nogate.py", "^BUILD: PASS"), st("next", "ok.py", "missing/bad=0")])
    runner.serve(run["run_id"])
    assert states(run["run_id"]) == ["failed", "queued"]
    assert "no gate line" in store.load_run(run["run_id"])["stages"][0]["note"]


def test_gate_and_action_lines_with_a_time_stamp_prefix_are_recognised():
    spec = {"gate": "^RESULT: PASS", "warn_exit": 2}
    state, gate, _, _ = runner.classify(spec, 0, ["[   0.062] PASS boot/sync", "[   2.937] RESULT: PASS (6/6 passed, 1 skipped)"])
    assert state == "passed" and gate == "RESULT: PASS (6/6 passed, 1 skipped)"
    state, gate, _, _ = runner.classify(spec, 1, ["[   2.937] RESULT: FAIL (5/6 passed)"])
    assert state == "failed" and gate == "RESULT: FAIL (5/6 passed)"
    state, _, action, _ = runner.classify(spec, 10, ["[   0.015] ACTION: CONNECT plug the board"])
    assert state == "waiting" and action["kind"] == "CONNECT"


def test_action_waits_and_approval_is_bound_to_the_image_and_used_once(tmp_path, monkeypatch):
    run = provider(tmp_path, monkeypatch, [
        st("create", "create.py", "Created "),
        st("flash", "flash.py", "^FLASH: PASS", approve_flag="--yes", binds="out/*.elf", evidence="flashed")])
    run_id = run["run_id"]
    runner.serve(run_id)
    run = store.load_run(run_id)
    assert states(run_id) == ["passed", "waiting"] and run["stages"][1]["action"]["kind"] == "APPROVE"
    runner.serve(run_id)                                     # no approval: nothing runs, no --yes ever added
    assert store.load_run(run_id)["stages"][1]["attempts"] == 1
    store.approve(run, "flash")
    image = tmp_path / "ws" / "demo" / "out" / "app.elf"
    image.write_bytes(b"image-2")                            # the image changed after the approval
    runner.serve(run_id)
    run = store.load_run(run_id)
    assert states(run_id) == ["passed", "waiting"] and "approve again" in run["stages"][1]["note"] and not run["approvals"]
    store.approve(run, "flash")
    runner.serve(run_id)
    run = store.load_run(run_id)
    assert states(run_id) == ["passed", "passed"] and not run["approvals"] and store.evidence(run) == "flashed"
    started = [e for e in store.events(run_id) if e["event"] == "stage_started" and e["stage"] == "flash"]
    assert [e["approved"] for e in started] == [False, True]


def test_connect_action_cannot_be_approved_only_retried(tmp_path, monkeypatch):
    run = provider(tmp_path, monkeypatch, [st("connect", "connect.py", "^IDENTITY: PASS")])
    runner.serve(run["run_id"])
    run = store.load_run(run["run_id"])
    assert run["stages"][0]["state"] == "waiting" and run["stages"][0]["action"]["kind"] == "CONNECT"
    with pytest.raises(ValueError):
        store.approve(run, "connect")
    store.retry(run, "connect")
    assert states(run["run_id"]) == ["queued"]


def test_fail_stops_the_chain_and_skip_stays_visible(tmp_path, monkeypatch):
    run = provider(tmp_path, monkeypatch, [st("build", "fail.py", "^BUILD: PASS", evidence="built"),
                                           st("test", "warn.py", "^RESULT: PASS", warn_exit=2)])
    run_id = run["run_id"]
    runner.serve(run_id)
    assert states(run_id) == ["failed", "queued"] and store.load_run(run_id)["stages"][0]["gate"] == "BUILD: FAIL"
    run = store.load_run(run_id)
    store.skip(run, "build")
    runner.serve(run_id)
    run = store.load_run(run_id)
    assert states(run_id) == ["skipped", "warnings"] and store.evidence(run) == "none" and store.summary(run) == "warnings"


def test_cancel_stops_the_process_and_interrupted_is_never_passed(tmp_path, monkeypatch):
    import threading
    import time
    run = provider(tmp_path, monkeypatch, [st("build", "slow.py", "^BUILD: PASS")])
    run_id = run["run_id"]
    thread = threading.Thread(target=runner.serve, args=(run_id,))
    thread.start()
    deadline = time.time() + 20
    while time.time() < deadline and states(run_id) != ["running"]:
        time.sleep(0.1)
    assert store.runner_alive(run_id)
    store.request_cancel(run_id)
    thread.join(20)
    assert states(run_id) == ["cancelled"] and not store.runner_alive(run_id)
    run = store.load_run(run_id)
    run["stages"][0]["state"] = "running"                    # as if the runner had died mid-stage
    store.save_run(run)
    assert store.recover(run) and states(run_id) == ["failed"]


def test_real_manifests_load_and_name_existing_scripts():
    manifests = store.load_manifests()
    assert set(manifests) == {"bare-metal", "freertos", "rt-thread", "emblinux"}
    for manifest in manifests.values():
        repo = store.provider_repo(manifest)
        if not repo.is_dir():
            pytest.skip(f"provider repository not on this PC: {repo}")
        for target in manifest["targets"]:
            scripts = repo / "skills" / target["skill"] / "scripts"
            for spec in manifest["stages"]:
                if spec.get("builtin"):
                    continue
                script = next(part for part in spec["argv"] if part.startswith("{scripts}/"))
                assert (scripts / script.split("/", 1)[1]).is_file(), f"{manifest['id']}: {script}"
            for template in target["templates"]:
                assert (repo / "skills" / target["skill"] / "templates" / template).is_dir()


def test_flows_pick_their_stages_and_delete_asks_first(tmp_path, monkeypatch):
    run = provider(tmp_path, monkeypatch, [st("create", "create.py", "Created ", evidence="created")])
    manifest_file = tmp_path / "providers" / "fake.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["stages"] += [st("ide", "ok.py", "missing/bad=0"),
                           {"id": "delete", "label": "delete", "builtin": "delete_app", "marker": "fake-app.env",
                            "approve_flag": "--yes", "gate": "^DELETE: done"}]
    manifest["flows"] = {"auto": ["create", "delete"], "ide": ["create", "ide"]}
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    ide = store.new_run("fake", "fake-board", "blink", "demo", "ide")
    assert [s["id"] for s in ide["stages"]] == ["create", "ide"]
    assert [r["run_id"] for r in store.list_runs("ide")] == [ide["run_id"]] and len(store.list_runs("auto")) == 1
    with pytest.raises(ValueError):
        store.new_run("fake", "fake-board", "blink", "demo", "nope")
    auto = store.new_run("fake", "fake-board", "blink", "demo")
    run_id, folder = auto["run_id"], tmp_path / "ws" / "demo"
    runner.serve(run_id)                                     # create passes; delete has no marker file -> refuses
    assert states(run_id) == ["passed", "failed"] and folder.is_dir()
    (folder / "fake-app.env").write_text("APP=demo", encoding="utf-8")
    store.retry(store.load_run(run_id), "delete")
    runner.serve(run_id)
    run = store.load_run(run_id)
    assert states(run_id) == ["passed", "waiting"] and run["stages"][1]["action"]["kind"] == "APPROVE" and folder.is_dir()
    store.approve(run, "delete")
    runner.serve(run_id)
    assert states(run_id) == ["passed", "passed"] and not folder.exists() and (tmp_path / "ws").is_dir()
    assert store.evidence(store.load_run(run_id)) == "created"


def test_app_name_and_target_are_checked(tmp_path, monkeypatch):
    provider(tmp_path, monkeypatch, [st("tools", "ok.py", "missing/bad=0")])
    for bad in ("X", "Has Space", "a", "toolongname-toolongname-x"):
        with pytest.raises(ValueError):
            store.new_run("fake", "fake-board", "blink", bad)
    with pytest.raises(ValueError):
        store.new_run("fake", "other-board", "blink", "demo")
    with pytest.raises(ValueError):
        store.new_run("fake", "fake-board", "nope", "demo")
    assert sys.executable in store.command(store.list_runs()[0], "tools")
