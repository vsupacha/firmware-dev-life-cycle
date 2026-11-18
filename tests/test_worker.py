import copy
import json
import os

import pytest

from reqstudio import bridge, capabilities as cap, contracts as c, worker


@pytest.fixture
def job(tmp_path, monkeypatch):
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path / 'data'))
    actual = cap.load_snapshot(cap.list_snapshots()[0])
    p = c.new_project(actual, 'Worker test')
    p['background_agent_consent'] = {'granted': True, 'destination': 'OpenAI Codex service'}
    p['messages'] = [{'id': 'TURN-worker', 'role': 'user', 'content': 'Need a button LED demonstration'}]
    bridge.enqueue(p, 'TURN-worker', None, backend='background')
    c.save_project(p)
    monkeypatch.setattr(worker, 'executable', lambda: 'fake-codex')
    return p, bridge.inbox()[0]


class Done:
    returncode = 0
    def poll(self): return self.returncode


def successful_launcher(command, **kwargs):
    assert '--sandbox' in command and command[command.index('--sandbox') + 1] == 'read-only'
    assert not any('bypass' in x for x in command)
    assert kwargs.get('shell', False) is False
    assert b'Need a button' in kwargs['stdin'].read()
    output = command[command.index('--output-last-message') + 1]
    from pathlib import Path
    Path(output).write_text(json.dumps({'reply': 'Who uses this?', 'questions': [], 'proposals': []}), encoding='utf8')
    return Done()


def test_worker_completes_without_chat_or_http_client(job, monkeypatch):
    p, item = job
    monkeypatch.setattr('reqstudio.llm.acquire', lambda *a, **k: pytest.fail('HTTP LLM client must not be called'))
    worker.run_job(item, 'worker-test', 30, lambda *a, **k: None, launcher=successful_launcher)
    saved = worker.load_project(p['project_id'])
    assert saved['agent_request']['status'] == 'completed'
    assert saved['messages'][-1]['content'] == 'Who uses this?'
    assert saved['stories'] == []


def test_cli_failure_is_visible_and_not_retried(job):
    p, item = job
    def failing(*a, **k):
        done = Done(); done.returncode = 1; return done
    worker.run_job(item, 'worker-test', 30, lambda *a, **k: None, launcher=failing)
    saved = worker.load_project(p['project_id'])
    assert saved['agent_request']['status'] == 'failed'
    assert 'CLI exited' in saved['agent_request']['error']
    assert not bridge.inbox()
    assert len(saved['messages']) == 1


def test_invalid_cli_json_cannot_modify_stories(job):
    p, item = job
    def invalid(command, **kwargs):
        from pathlib import Path
        Path(command[command.index('--output-last-message') + 1]).write_text('not JSON', encoding='utf8')
        return Done()
    worker.run_job(item, 'worker-test', 30, lambda *a, **k: None, launcher=invalid)
    saved = worker.load_project(p['project_id'])
    assert saved['agent_request']['status'] == 'failed'
    assert saved['stories'] == [] and saved['proposals'] == []


class Running:
    returncode = None
    killed = False
    def poll(self): return self.returncode


@pytest.mark.parametrize('reason', ['cancel', 'context', 'timeout', 'stop'])
def test_worker_stops_obsolete_or_cancelled_child(job, monkeypatch, reason):
    p, item = job
    child = Running()
    def launch(*a, **k):
        if reason in {'cancel', 'context'}:
            live = worker.load_project(p['project_id'])
            if reason == 'cancel': live['agent_request']['status'] = 'cancelled'
            else: live['constraints'] = ['Changed while agent is running']
            c.save_project(live)
        return child
    def kill(proc):
        proc.killed = True; proc.returncode = -15
    monkeypatch.setattr(worker, 'kill_child', kill)
    monkeypatch.setattr(worker, 'stop_requested', lambda _: reason == 'stop')
    worker.run_job(item, 'worker-test', -1 if reason == 'timeout' else 30, lambda *a, **k: None, launcher=launch)
    assert child.killed
    saved = worker.load_project(p['project_id'])
    assert saved['agent_request']['status'] == {'cancel': 'cancelled', 'context': 'stale', 'timeout': 'failed', 'stop': 'cancelled'}[reason]
    assert len(saved['messages']) == 1


def test_only_claiming_worker_can_publish(job):
    p, item = job
    rid = item['request']['id']
    worker.set_request_state(p['project_id'], rid, 'processing', 'owner')
    with pytest.raises(ValueError, match='no longer current'):
        bridge.respond(p['project_id'], rid, {'reply': 'wrong worker', 'questions': [], 'proposals': []}, worker_id='other')
    live = worker.load_project(p['project_id'])
    with pytest.raises(ValueError, match='already pending'):
        bridge.enqueue(live, 'TURN-worker', None, backend='background')


def test_dead_worker_request_is_recovered_as_failed(job, monkeypatch):
    p, item = job
    worker.set_request_state(p['project_id'], item['request']['id'], 'processing', 'dead-owner')
    monkeypatch.setattr(worker, 'pid_alive', lambda _: False)
    worker.recover_interrupted()
    assert worker.load_project(p['project_id'])['agent_request']['status'] == 'failed'


def test_singleton_lock_does_not_replace_live_owner(tmp_path):
    lock = tmp_path / 'worker.lock'
    token = worker.acquire_lock(lock)
    with pytest.raises(ValueError, match='busy'):
        worker.acquire_lock(lock)
    worker.release_lock(lock, 'not-owner')
    assert lock.exists()
    worker.release_lock(lock, token)
    assert not lock.exists()


def test_ui_background_mode_enqueues_without_api(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    monkeypatch.setattr('reqstudio.llm.acquire', lambda *a, **k: pytest.fail('No direct HTTP call'))
    app = AppTest.from_file(str(cap.ROOT / 'streamlit_app.py'), default_timeout=20).run()
    next(w for w in app.selectbox if w.label == 'Agent').select('Background agent / CLI').run()
    next(w for w in app.checkbox if w.label.startswith('อนุญาตให้ส่ง')).check().run()
    app.chat_input[0].set_value('Need a button LED demonstration').run()
    assert not app.exception
    item = bridge.inbox()[0]
    assert item['request']['backend'] == 'background'
    monkeypatch.setattr(worker, 'executable', lambda: 'fake-codex')
    worker.run_job(item, 'worker-ui-test', 30, lambda *a, **k: None, launcher=successful_launcher)
    app.run()
    assert not app.exception
    assert c.load_projects()[0]['agent_request']['status'] == 'completed'


def test_ui_transfers_pending_legacy_request_to_selected_background_mode(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    snapshot = cap.load_snapshot(cap.list_snapshots()[0])
    project = c.new_project(snapshot)
    project['messages'] = [{'id': 'TURN-migrate', 'role': 'user', 'content': 'Already submitted user requirement'}]
    request = bridge.enqueue(project, 'TURN-migrate', None)
    c.save_project(project)
    app = AppTest.from_file(str(cap.ROOT / 'streamlit_app.py'), default_timeout=20).run()
    next(w for w in app.selectbox if w.label == 'Agent').select('Background agent / CLI').run()
    assert not app.exception
    saved = c.load_projects()[0]
    assert saved['agent_request']['id'] == request['id']
    assert saved['agent_request']['backend'] == 'background'
    assert saved['messages'] == project['messages']

def test_unapproved_draft_never_launches_cli(job):
    project, item = job
    project = worker.load_project(project['project_id'])
    project['background_agent_consent'] = {'granted': False, 'destination': 'OpenAI Codex service'}
    c.save_project(project)
    def forbidden(*a, **k):
        pytest.fail('Unapproved draft must never launch CLI')
    worker.run_job(item, 'worker-test', 30, lambda *a, **k: None, launcher=forbidden)
    assert worker.load_project(project['project_id'])['agent_request']['status'] == 'pending'


def test_external_authorization_is_not_revoked_by_stale_widget(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    app = AppTest.from_file(str(cap.ROOT / 'streamlit_app.py'), default_timeout=20).run()
    next(w for w in app.selectbox if w.label == 'Agent').select('Background agent / CLI').run()
    project = c.load_projects()[0]
    project['background_agent_consent'] = {'granted': True, 'destination': 'OpenAI Codex service', 'updated_at_utc': cap.utc_now()}
    c.save_project(project)
    app.run()
    assert not app.exception
    assert worker.authorized(c.load_projects()[0])
    assert next(w for w in app.checkbox if w.label.startswith('อนุญาตให้ส่ง')).value


def test_status_publication_failure_does_not_fail_successful_job(job, monkeypatch):
    import errno
    project, item = job
    def locked(*args):
        raise PermissionError(errno.EACCES, 'temporary heartbeat lock')
    monkeypatch.setattr(worker, 'atomic_json', locked)
    state = {'pid': os.getpid()}
    worker.run_job(item, 'worker-test', 30, lambda mode, **extra: worker.publish_status(state, mode, **extra), launcher=successful_launcher)
    saved = worker.load_project(project['project_id'])
    assert saved['agent_request']['status'] == 'completed'
    assert saved['messages'][-1]['content'] == 'Who uses this?'
