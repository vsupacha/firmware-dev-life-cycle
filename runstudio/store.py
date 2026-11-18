"""Provider manifests and durable run records for the Auto and IDE pages.

A run is one app on one board: a folder <data>/runs/<run_id>/ with
    run.json        the record (stages, states, approvals); written atomically
    events.jsonl    append-only history of every state change
    logs/           one raw log per stage attempt
The UI only reads and writes these files; `runstudio.runner` executes the stages in its own
process, so a run continues when the browser closes. A stage is passed only by its script's exit
code and gate line - nothing here can mark a stage passed by hand.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from reqstudio.worker import atomic_json, read_json

ROOT = Path(__file__).resolve().parents[1]
STATES = ("queued", "running", "passed", "warnings", "failed", "waiting", "skipped", "cancelled")
EVIDENCE = ("none", "created", "built", "flashed", "tested")
APP_NAME = re.compile(r"^[a-z][a-z0-9-]{1,19}$")
HEARTBEAT_STALE_S = 8


def data_directory() -> Path:
    return Path(os.environ.get("FWLC_DATA_DIR", str(Path.home() / ".firmware-dev-life-cycle"))).expanduser()


def runs_directory() -> Path:
    return data_directory() / "runs"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ---- provider manifests -------------------------------------------------------------------------

def manifests_directory() -> Path:
    return Path(os.environ.get("FWLC_PROVIDERS_DIR", str(ROOT / "providers")))


def load_manifests() -> dict[str, dict]:
    values = {}
    for path in sorted(manifests_directory().glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema") != 1:
            continue
        ids = [s["id"] for s in value["stages"]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{path.name}: duplicate stage id")
        value.setdefault("flows", {"auto": ids})
        for name, flow in value["flows"].items():
            if set(flow) - set(ids):
                raise ValueError(f"{path.name}: flow {name!r} names an unknown stage")
        value["_file"] = str(path)
        values[value["id"]] = value
    return values


def provider_repo(manifest: dict) -> Path:
    override = os.environ.get(manifest.get("env", ""), "")
    if override:
        return Path(override).resolve()
    base = Path(manifest["_file"]).resolve().parent.parent
    return (base / manifest["repo"]).resolve()


def workspace() -> Path | None:
    """This PC's apps workspace, the same rule as the provider scripts (FW_WS, then ~/.fw-skills.env)."""
    if os.environ.get("FW_WS"):
        return Path(os.environ["FW_WS"])
    settings = Path(os.environ.get("FW_SETTINGS", str(Path.home() / ".fw-skills.env")))
    if settings.is_file():
        for line in settings.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("FW_WS="):
                return Path(line.split("=", 1)[1].strip().strip('"'))
    return None


def find_bash() -> str:
    """Git Bash, never WSL's bash.exe in System32 (the provider scripts need Git Bash on Windows)."""
    if os.environ.get("FWLC_BASH"):
        return os.environ["FWLC_BASH"]
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("LOCALAPPDATA", "") + r"\Programs"):
            candidate = Path(base) / "Git" / "bin" / "bash.exe"
            if candidate.is_file():
                return str(candidate)
    return shutil.which("bash") or "bash"


def target_of(manifest: dict, board: str) -> dict:
    for target in manifest["targets"]:
        if target["board"] == board:
            return target
    raise ValueError(f"board {board!r} is not a target of provider {manifest['id']!r}")


def flow_stages(manifest: dict, flow: str) -> list[str]:
    """Labels of the stages one flow runs, in order."""
    by_id = {s["id"]: s["label"] for s in manifest["stages"]}
    return [by_id[i] for i in manifest["flows"].get(flow, [])]


# ---- run records --------------------------------------------------------------------------------

def run_dir(run_id: str) -> Path:
    if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}", run_id):
        raise ValueError("Invalid run ID")
    return runs_directory() / run_id


def new_run(provider_id: str, board: str, template: str, app: str, flow: str = "auto") -> dict:
    manifests = load_manifests()
    if provider_id not in manifests:
        raise ValueError(f"Unknown provider {provider_id!r}")
    manifest = manifests[provider_id]
    target = target_of(manifest, board)
    if flow not in manifest["flows"]:
        raise ValueError(f"Provider {provider_id!r} has no flow {flow!r}")
    specs = {s["id"]: s for s in manifest["stages"]}
    if template not in target["templates"]:
        raise ValueError(f"Template {template!r} is not offered for {board}")
    if not APP_NAME.fullmatch(app):
        raise ValueError("App name: 2-20 characters, lower-case letters, digits and '-', starting with a letter")
    if not (provider_repo(manifest) / "skills" / target["skill"] / "scripts").is_dir():
        raise ValueError(f"Provider skill folder not found: {provider_repo(manifest) / 'skills' / target['skill']}")
    ws = workspace()
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    run = {"schema": 1, "run_id": run_id, "created": now(), "updated": now(), "provider": provider_id, "flow": flow,
           "provider_label": manifest["label"], "board": board, "board_label": target.get("label", board),
           "skill": target["skill"], "template": template, "app": app,
           "app_dir": str(ws / app).replace("\\", "/") if ws else "",
           "manifest_sha256": hashlib.sha256(Path(manifest["_file"]).read_bytes()).hexdigest(),
           "stages": [{"id": s["id"], "label": s["label"], "state": "queued", "attempts": 0, "gate": "", "exit": None,
                       "action": None, "note": "", "started": "", "ended": "", "seconds": None, "log": ""}
                      for s in (specs[i] for i in manifest["flows"][flow])],
           "approvals": {}}
    folder = run_dir(run_id)
    (folder / "logs").mkdir(parents=True)
    atomic_json(folder / "run.json", run)
    append_event(run_id, {"event": "created", "flow": flow, "provider": provider_id, "board": board, "template": template, "app": app})
    return run


def load_run(run_id: str) -> dict | None:
    return read_json(run_dir(run_id) / "run.json")


def save_run(run: dict) -> None:
    run["updated"] = now()
    atomic_json(run_dir(run["run_id"]) / "run.json", run)


def list_runs(flow: str | None = None) -> list[dict]:
    """All runs, newest first; with `flow`, only that flow's (records from before flows count as "auto")."""
    values = []
    for path in runs_directory().glob("*/run.json"):
        value = read_json(path)
        if value and value.get("schema") == 1 and flow in (None, value.get("flow", "auto")):
            values.append(value)
    return sorted(values, key=lambda r: r["run_id"], reverse=True)


def append_event(run_id: str, event: dict) -> None:
    line = json.dumps({"at": now(), **event}, ensure_ascii=False)
    with (run_dir(run_id) / "events.jsonl").open("a", encoding="utf-8", newline="\n") as output:
        output.write(line + "\n")


def events(run_id: str) -> list[dict]:
    path = run_dir(run_id) / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def stage(run: dict, stage_id: str) -> dict:
    return next(s for s in run["stages"] if s["id"] == stage_id)


def stage_spec(run: dict, stage_id: str) -> dict:
    manifest = load_manifests()[run["provider"]]
    return next(s for s in manifest["stages"] if s["id"] == stage_id)


def next_stage(run: dict) -> dict | None:
    """The first stage that is not passed or skipped (the one the runner would look at next)."""
    return next((s for s in run["stages"] if s["state"] not in ("passed", "skipped")), None)


def summary(run: dict) -> str:
    states = [s["state"] for s in run["stages"]]
    for state in ("running", "waiting", "failed", "warnings", "cancelled"):
        if state in states:
            return state
    if all(s in ("passed", "skipped") for s in states):
        return "done"
    return "idle"


def evidence(run: dict) -> str:
    """Highest evidence level reached by passed stages, in stage order (a skipped stage adds none)."""
    manifest = load_manifests().get(run["provider"])
    level = "none"
    if not manifest:
        return level
    specs = {s["id"]: s for s in manifest["stages"]}
    for record in run["stages"]:
        spec = specs.get(record["id"], {})
        if record["state"] == "passed" and spec.get("evidence"):
            if EVIDENCE.index(spec["evidence"]) > EVIDENCE.index(level):
                level = spec["evidence"]
    return level


# ---- placeholders, artifacts, approvals ----------------------------------------------------------

def substitutions(run: dict) -> dict[str, str]:
    manifest = load_manifests()[run["provider"]]
    repo = provider_repo(manifest)
    return {"bash": find_bash(), "python": sys.executable, "repo": repo.as_posix(),
            "scripts": (repo / "skills" / run["skill"] / "scripts").as_posix(), "board": run["board"],
            "app": run["app"], "app_dir": run["app_dir"], "template": run["template"],
            "spec": run["template"].replace("-", "_"), "ts": time.strftime("%Y%m%d-%H%M%S")}


def command(run: dict, stage_id: str, approved: bool = False) -> list[str]:
    spec, values = stage_spec(run, stage_id), substitutions(run)
    if spec.get("builtin") == "delete_app":                    # the manager's own per-app step (runstudio/builtin.py)
        ws = workspace()
        return ([sys.executable, "-B", str(ROOT / "runstudio" / "builtin.py"), "delete_app", run["app_dir"],
                 str(ws) if ws else "", spec["marker"]] + ([spec["approve_flag"]] if approved else []))
    argv = [part.format(**values) for part in spec["argv"]]
    if approved and spec.get("approve_flag"):
        argv.append(spec["approve_flag"])
    return argv


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def bound_file(run: dict, stage_id: str) -> Path | None:
    """The image an approval is tied to (manifest 'binds' glob inside the app folder), if any."""
    pattern = stage_spec(run, stage_id).get("binds")
    if not pattern or not run["app_dir"]:
        return None
    matches = sorted(glob.glob(str(Path(run["app_dir"]) / pattern)))
    return Path(matches[0]) if matches else None


def artifacts(run: dict) -> list[dict]:
    """Files named by the manifest's artifact globs, with the stage that produces them."""
    rows, seen = [], set()
    manifest = load_manifests().get(run["provider"])
    if not manifest or not run["app_dir"] or not Path(run["app_dir"]).is_dir():
        return rows
    base = Path(run["app_dir"])
    in_run = {record["id"] for record in run["stages"]}
    for spec in manifest["stages"]:
        if spec["id"] not in in_run:
            continue
        for pattern in spec.get("artifacts", []):
            for match in sorted(glob.glob(str(base / pattern))):
                path = Path(match)
                if not path.is_file() or path in seen:
                    continue
                seen.add(path)
                size = path.stat().st_size
                rows.append({"stage": spec["id"], "file": path.relative_to(base).as_posix(), "bytes": size,
                             "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime)),
                             "sha256": file_sha256(path) if size <= 64 * 1024 * 1024 else "", "path": str(path)})
    return rows


def approve(run: dict, stage_id: str) -> None:
    """Record the developer's yes for one waiting stage, tied to the action text and the image hash."""
    record = stage(run, stage_id)
    if record["state"] != "waiting" or not record["action"] or record["action"]["kind"] != "APPROVE":
        raise ValueError("Only a stage waiting on ACTION: APPROVE can be approved")
    if not stage_spec(run, stage_id).get("approve_flag"):
        raise ValueError("This stage has no approval flag in the manifest")
    bound = bound_file(run, stage_id)
    run["approvals"][stage_id] = {"at": now(), "action": record["action"]["text"], "board": run["board"],
                                 "file": str(bound) if bound else "", "sha256": file_sha256(bound) if bound else ""}
    save_run(run)
    append_event(run["run_id"], {"event": "approved", "stage": stage_id, "sha256": run["approvals"][stage_id]["sha256"]})


def retry(run: dict, stage_id: str) -> None:
    """Queue a stopped stage again (a new attempt; earlier logs are kept)."""
    record = stage(run, stage_id)
    if record["state"] not in ("failed", "warnings", "waiting", "cancelled", "skipped"):
        raise ValueError("Only a stopped stage can be retried")
    run["approvals"].pop(stage_id, None)
    record.update(state="queued", action=None, note="")
    save_run(run)
    append_event(run["run_id"], {"event": "retry", "stage": stage_id})


def skip(run: dict, stage_id: str) -> None:
    record = stage(run, stage_id)
    if record["state"] in ("passed", "running"):
        raise ValueError("A passed or running stage cannot be skipped")
    run["approvals"].pop(stage_id, None)
    record.update(state="skipped", action=None, note="skipped by the developer")
    save_run(run)
    append_event(run["run_id"], {"event": "skipped", "stage": stage_id})


# ---- runner process ------------------------------------------------------------------------------

def heartbeat_file(run_id: str) -> Path:
    return run_dir(run_id) / "runner.heartbeat"


def runner_alive(run_id: str) -> bool:
    path = heartbeat_file(run_id)
    return path.is_file() and time.time() - path.stat().st_mtime < HEARTBEAT_STALE_S


def request_cancel(run_id: str) -> None:
    (run_dir(run_id) / "cancel.request").write_text(now(), encoding="utf-8")
    append_event(run_id, {"event": "cancel_requested"})


def start_runner(run_id: str, one_stage: bool = False) -> None:
    """Start the detached runner for this run (no-op when one is already alive)."""
    if runner_alive(run_id):
        return
    argv = [sys.executable, "-B", "-m", "runstudio.runner", run_id] + (["--one"] if one_stage else [])
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    log = (run_dir(run_id) / "runner.log").open("a", encoding="utf-8")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    subprocess.Popen(argv, cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                     creationflags=flags, env=env, close_fds=True)
    heartbeat_file(run_id).write_text(now(), encoding="utf-8")       # the UI shows "running" at once


def recover(run: dict) -> bool:
    """A stage left 'running' with no live runner did not finish: mark it failed, never passed."""
    changed = False
    if runner_alive(run["run_id"]):
        return changed
    for record in run["stages"]:
        if record["state"] == "running":
            record.update(state="failed", note="interrupted: the runner stopped before this stage ended")
            changed = True
    if changed:
        save_run(run)
        append_event(run["run_id"], {"event": "interrupted"})
    return changed
