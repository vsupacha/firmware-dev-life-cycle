import copy
import hashlib
import io
import json
import os
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from reqstudio import capabilities as cap
from reqstudio import contracts as c
from reqstudio import llm


@pytest.fixture
def snapshot():
    return {"schema_version": 1, "snapshot_id": "CAP-TEST", "captured_at_utc": "2026-10-31T08:00:00+00:00",
            "captured_at_bangkok": "2026-10-31T15:00:00+07:00", "provider_revision": None,
            "fingerprint": cap.fingerprint([]), "active_milestones": ["M1"], "readiness": "not_probed", "sources": [], "source_notes": [],
            "boards": [{"id": "board-a", "profiles": {"test-framework-board": {"level": "built", "templates": {"push-to-light": "built"}}}}],
            "skills": [{"id": "test-framework-board", "kind": "board", "description": "demo", "boards": [{"board_id": "board-a", "level": "built", "templates": {"push-to-light": "built"}}], "templates": ["push-to-light"], "operations": {"build": True}}],
            "driver_recipes": []}


@pytest.fixture
def ready(snapshot):
    p = c.new_project(snapshot)
    p["board_id"] = "board-a"
    s = c.add_story(p)
    c.update_story(s, {"title": "Button LED", "role": "tester", "want": "control LED by button", "benefit": "check input/output",
                       "acceptance_criteria": [{"text": "Press turns LED on", "test_intent": "Press and observe physical LED", "requires_hardware": True}],
                       "feasibility": "supported", "feasibility_reason": "Imported recipe scope; target execution still pending",
                       "capability_refs": ["template:test-framework-board/push-to-light"], "reviewed": True})
    return p


def fresh(status="current"):
    return {"status": status, "checked_at_utc": cap.utc_now(), "changed": [], "added": [], "removed": []}


def test_capture_detects_content_drift_not_just_timestamps(tmp_path):
    provider = tmp_path / "provider"
    (provider / "boards").mkdir(parents=True)
    (provider / "docs").mkdir()
    index = provider / "boards/index.json"
    index.write_text('{"boards": []}', encoding="utf-8")
    doc = provider / "docs/workflow.md"
    doc.write_text("# First", encoding="utf-8")
    (provider / "CLAUDE.local.md").write_text("private handoff", encoding="utf-8")
    snap = cap.capture(provider)
    assert not any("CLAUDE.local" in x["path"] for x in snap["sources"])
    os.utime(doc, None)
    assert cap.compare(snap, provider)["status"] == "current"
    doc.write_text("# Updated", encoding="utf-8")
    assert cap.compare(snap, provider)["changed"] == ["docs/workflow.md"]
    doc.unlink()
    (provider / "docs/new.md").write_text("new", encoding="utf-8")
    drift = cap.compare(snap, provider)
    assert drift["removed"] == ["docs/workflow.md"] and drift["added"] == ["docs/new.md"]


def test_snapshots_are_immutable(snapshot, tmp_path):
    paths = cap.write_snapshot(snapshot, tmp_path)
    assert "Captured Bangkok" in paths[1].read_text(encoding="utf-8")
    assert cap.load_snapshot(paths[0])["snapshot_id"] == snapshot["snapshot_id"]
    with pytest.raises(ValueError, match="immutable"):
        cap.write_snapshot(snapshot, tmp_path)


@pytest.mark.parametrize("change", ["questions", "review", "feasibility", "intent", "reference"])
def test_incomplete_requirement_cannot_be_offered(ready, snapshot, change):
    s = ready["stories"][0]
    if change == "questions": s["open_questions"] = ["Which LED?"]
    if change == "review": s["reviewed"] = False
    if change == "feasibility": s["feasibility"] = "needs-spike"
    if change == "intent": s["acceptance_criteria"][0]["test_intent"] = ""
    if change == "reference": s["capability_refs"] = ["driver:invented/feature"]
    with pytest.raises(ValueError):
        c.make_handoff(ready, snapshot, fresh())


def test_handoff_pending_acceptance_and_portable_bundle(ready, snapshot):
    value = c.make_handoff(ready, snapshot, fresh("unavailable"))
    assert value["consumer_acceptance"] == "pending"
    assert value["readiness"] == "not_probed"
    assert "unavailable" in value["design_checks"][0]
    with zipfile.ZipFile(io.BytesIO(c.handoff_bundle(value, snapshot))) as z:
        manifest = json.loads(z.read("manifest.json"))
        for name, sha in manifest["sha256"].items():
            assert hashlib.sha256(z.read(name)).hexdigest() == sha
        assert json.loads(z.read("capability_snapshot.json"))["snapshot_id"] == "CAP-TEST"
    from scripts.validate_handoff import validate_bundle
    assert validate_bundle(c.handoff_bundle(value, snapshot))["consumer_acceptance"] == "pending"


def test_corrupt_bundle_is_rejected(ready, snapshot):
    from scripts.validate_handoff import validate_bundle
    value = c.make_handoff(ready, snapshot, fresh())
    original = c.handoff_bundle(value, snapshot)
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(buffer, "w") as target:
        for name in source.namelist():
            target.writestr(name, b"changed" if name == "requirements.md" else source.read(name))
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_bundle(buffer.getvalue())


def test_changed_provider_blocks_handoff(ready, snapshot):
    with pytest.raises(ValueError, match="Provider sources changed"):
        c.make_handoff(ready, snapshot, fresh("changed"))


def test_rebind_invalidates_review_and_proposals(ready, snapshot):
    ready["proposals"] = [{"some": "old context"}]
    new = {**snapshot, "snapshot_id": "CAP-NEW"}
    c.rebind_snapshot(ready, new)
    assert not ready["stories"][0]["reviewed"]
    assert ready["stories"][0]["feasibility"] == "unknown"
    assert not ready["proposals"]


def test_persistence_conflict_does_not_overwrite_saved_state(ready, tmp_path):
    c.save_project(ready, tmp_path)
    stale = copy.deepcopy(ready)
    ready["name"] = "New name"
    c.save_project(ready, tmp_path)
    stale["name"] = "Stale name"
    with pytest.raises(ValueError, match="Another tab"):
        c.save_project(stale, tmp_path)
    assert c.load_projects(tmp_path)[0]["name"] == "New name"


def test_stale_handoff_leaves_no_orphan_zip(ready, snapshot, tmp_path):
    c.save_project(ready, tmp_path)
    stale = copy.deepcopy(ready)
    c.save_project(ready, tmp_path)
    with pytest.raises(ValueError, match="Another tab"):
        c.store_handoff(stale, c.make_handoff(stale, snapshot, fresh()), snapshot, tmp_path)
    assert not list(tmp_path.glob("projects/*/handoffs/*.zip"))


def test_constraint_change_invalidates_feasibility_review(ready):
    c.update_context(ready, ready["name"], ready["board_id"], ["Must work without an RTOS"])
    assert not ready["stories"][0]["reviewed"]
    assert ready["stories"][0]["feasibility"] == "unknown"


def proposal():
    return {"operation": "create", "story_id": None, "base_revision": None, "title": "Button LED", "role": "tester",
            "want": "control LED", "benefit": "check inputs", "acceptance_criteria": [{"text": "LED turns on", "test_intent": "Observe LED", "requires_hardware": True}],
            "open_questions": [], "feasibility": "unknown", "feasibility_reason": "Needs confirmation", "capability_refs": []}


def test_proposal_is_draft_and_stale_updates_are_rejected(ready, snapshot):
    p = {**proposal(), "operation": "update", "story_id": ready["stories"][0]["id"], "base_revision": 1}
    with pytest.raises(ValueError, match="stale"):
        c.apply_proposal(ready, p, snapshot)
    p["base_revision"] = ready["stories"][0]["revision"]
    s = c.apply_proposal(ready, p, snapshot)
    assert not s["reviewed"]


def test_model_json_invalid_output_never_applies(ready):
    original = copy.deepcopy(ready)
    with pytest.raises(ValueError, match="valid JSON"):
        llm.parse_response("I think this is done")
    assert ready == original


@pytest.fixture
def local_server():
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            data = {"models": [{"name": "test-local"}]} if self.path == "/api/tags" else {"data": [{"id": "test-local"}]}
            self.respond(data)
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append((self.path, body))
            content = json.dumps({"reply": "Please review the proposal", "questions": [], "proposals": [proposal()]})
            data = {"message": {"content": content}} if self.path == "/api/chat" else {"choices": [{"message": {"content": content}}]}
            self.respond(data)
        def respond(self, data):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", calls
    server.shutdown()
    server.server_close()


@pytest.mark.parametrize("provider,path", [("Ollama", "/api/chat"), ("OpenAI-compatible", "/v1/chat/completions")])
def test_local_protocol_adapters(local_server, ready, snapshot, provider, path):
    endpoint, calls = local_server
    assert llm.list_models(provider, endpoint) == ["test-local"]
    result = llm.acquire(provider, endpoint, "test-local", ready, snapshot, None)
    assert len(result["proposals"]) == 1
    assert calls[0][0] == path
    assert calls[0][1]["stream"] is False
    assert "api_key" not in json.dumps(ready)


def button(app, label):
    return next(b for b in app.button if b.label == label)


def test_streamlit_manual_persistence_and_export(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    actual = cap.load_snapshot(cap.list_snapshots()[0])
    ready = c.new_project(actual, "UI test")
    board = next(b for b in actual["boards"] if cap.capability_options(actual, b["id"]))
    ready["board_id"] = board["id"]
    s = c.add_story(ready)
    c.update_story(s, {"title": "LED check", "role": "tester", "want": "check LED", "benefit": "verify output",
                       "acceptance_criteria": [{"text": "LED on", "test_intent": "Observe LED physically", "requires_hardware": True}],
                       "feasibility": "supported", "feasibility_reason": "Recipe mapping reviewed; behavior not tested",
                       "capability_refs": [next(iter(cap.capability_options(actual, board["id"])))], "reviewed": True})
    monkeypatch.setenv("FWLC_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FWLC_PROVIDER_ROOT", str(tmp_path / "not-available"))
    c.save_project(ready)
    app = AppTest.from_file(str(cap.ROOT / "streamlit_app.py"), default_timeout=20).run()
    assert not app.exception
    button(app, "สร้าง baseline และส่งเสนอให้ Design").click().run()
    assert not app.exception
    assert c.load_projects()[0]["baseline_revision"] == 1
    assert list((tmp_path / "data").glob("projects/*/handoffs/*.zip"))
    app.chat_input[0].set_value("ขอทบทวนสถานะหลัง reset").run()
    assert not app.exception
    assert len(c.load_projects()[0]["messages"]) == 2
    button(app, "โหลดล่าสุด").click().run()
    assert not app.exception


def test_streamlit_llm_proposal_requires_click(tmp_path, monkeypatch, local_server):
    from streamlit.testing.v1 import AppTest
    endpoint, _ = local_server
    monkeypatch.setenv("FWLC_DATA_DIR", str(tmp_path / "data"))
    app = AppTest.from_file(str(cap.ROOT / "streamlit_app.py"), default_timeout=20).run()
    next(w for w in app.selectbox if w.label == "Agent").select("Ollama").run()
    next(w for w in app.text_input if w.label == "Local server URL").set_value(endpoint).run()
    app.chat_input[0].set_value("อยากให้ปุ่มควบคุม LED").run()
    assert not app.exception
    assert not c.load_projects()[0]["stories"]
    assert len(c.load_projects()[0]["proposals"]) == 1
    button(app, "รับเป็น draft").click().run()
    assert not app.exception
    saved = c.load_projects()[0]
    assert len(saved["stories"]) == 1 and not saved["stories"][0]["reviewed"]
    assert saved["stories"][0]["source_turn_ids"]


def test_host_bridge_delivers_reply_without_applying_story(ready, monkeypatch, tmp_path):
    from reqstudio import bridge
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    ready['messages'].append({'id': 'TURN-real', 'role': 'user', 'content': 'Actual UI request'})
    request = bridge.enqueue(ready, 'TURN-real', None)
    c.save_project(ready)
    assert len(bridge.inbox()) == 1
    result = bridge.respond(ready['project_id'], request['id'], {'reply': 'Please review', 'questions': [], 'proposals': [proposal()]})
    assert result['agent_request']['status'] == 'completed'
    assert len(result['stories']) == 1  # pre-existing story only
    assert len(result['proposals']) == 1
    with pytest.raises(ValueError, match='no longer current'):
        bridge.respond(ready['project_id'], request['id'], {'reply': 'duplicate', 'questions': [], 'proposals': []})


def test_host_bridge_rejects_context_changes(ready, monkeypatch, tmp_path):
    from reqstudio import bridge
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    ready['messages'].append({'id': 'TURN-real', 'role': 'user', 'content': 'Actual UI request'})
    request = bridge.enqueue(ready, 'TURN-real', None)
    c.save_project(ready)
    c.update_context(ready, ready['name'], ready['board_id'], ['New constraint'])
    c.save_project(ready)
    with pytest.raises(ValueError, match='context changed'):
        bridge.respond(ready['project_id'], request['id'], {'reply': 'old response', 'questions': [], 'proposals': []})
    assert c.load_projects()[0]['agent_request']['status'] == 'stale'


def test_streamlit_host_mode_queues_actual_ui_message(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from reqstudio import bridge
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    app = AppTest.from_file(str(cap.ROOT / 'streamlit_app.py'), default_timeout=20).run()
    next(w for w in app.selectbox if w.label == 'Agent').select('Host agent / interactive').run()
    app.chat_input[0].set_value('อยากเริ่มจากระบบงานจริง').run()
    assert not app.exception
    request = bridge.inbox()[0]
    assert request['messages'][-1]['content'] == 'อยากเริ่มจากระบบงานจริง'
    assert app.chat_input[0].disabled
    bridge.respond(request['project_id'], request['request']['id'], {'reply': 'ใครเป็นผู้ใช้ระบบนี้ครับ?', 'questions': [], 'proposals': []})
    app.run()
    assert not app.exception
    assert c.load_projects()[0]['messages'][-1]['role'] == 'assistant'
