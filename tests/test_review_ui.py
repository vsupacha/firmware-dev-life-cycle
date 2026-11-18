import copy

from streamlit.testing.v1 import AppTest

from reqstudio import capabilities as cap, contracts as c, bridge


def button(app, label):
    return next(w for w in app.button if w.label == label)


def selectbox(app, label):
    return next(w for w in app.selectbox if w.label == label)


def launch(tmp_path, monkeypatch):
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    return AppTest.from_file(str(cap.ROOT / 'streamlit_app.py'), default_timeout=20).run()


def test_new_draft_repeated_clicks_url_and_form_isolation(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    original = app.session_state.project['project_id']
    first = c.load_projects()[0]
    first['messages'] = [{'id': 'USER-old', 'role': 'user', 'content': 'old draft only'}]
    c.save_project(first)
    app.query_params['project'] = original
    app.run()
    button(app, 'โหลดล่าสุด').click().run()
    assert not app.exception
    seen = {original}
    for _ in range(3):
        button(app, 'Draft ใหม่').click().run()
        assert not app.exception
        current = app.session_state.project
        assert current['project_id'] not in seen
        seen.add(current['project_id'])
        assert selectbox(app, 'Draft ที่บันทึกไว้').value == current['project_id']
        assert app.query_params['project'] == [current['project_id']]
        assert not current['messages'] and not current['stories']
        assert next(w for w in app.text_input if w.label == 'ชื่อโครงการ').value == current['name']
        app.run()
        assert app.session_state.project['project_id'] == current['project_id']
    selectbox(app, 'Draft ที่บันทึกไว้').select(original).run()
    assert not app.exception
    assert app.session_state.project['messages'][0]['content'] == 'old draft only'
    assert app.query_params['project'] == [original]
    assert len(c.load_projects()) == 4


def test_review_tables_and_selected_proposal_acceptance(tmp_path, monkeypatch):
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    snapshot = cap.load_snapshot(cap.list_snapshots()[0])
    project = c.new_project(snapshot, 'Multiple goals')
    existing = c.add_story(project)
    c.update_story(existing, {'title': 'Scan', 'role': 'surveyor', 'want': 'scan and save', 'benefit': 'record a survey'})
    def proposed(key, title, question):
        return {'id': key, 'operation': 'create', 'story_id': None, 'base_revision': None,
                'title': title, 'role': 'operator', 'want': title, 'benefit': 'manage surveys',
                'acceptance_criteria': [{'text': title + ' succeeds', 'test_intent': 'observe result', 'requires_hardware': True}],
                'open_questions': [question], 'feasibility': 'unknown', 'feasibility_reason': '', 'capability_refs': [],
                'source_turn_ids': ['USER-1'], 'snapshot_id': snapshot['snapshot_id'], 'board_id': '', 'model': 'synthetic'}
    project['proposals'] = [proposed('P-time', 'Set clock', 'What time format?'), proposed('P-clear', 'Clear logs', 'When is clear allowed?')]
    c.save_project(project)
    app = launch(tmp_path, monkeypatch)
    assert not app.exception
    assert len(app.tabs) == 5
    assert all(t.label != 'ตั้งค่า' for t in app.tabs)
    assert any(e.label == 'ตั้งค่า' for e in app.sidebar.expander)
    frames = [w.value for w in app.dataframe if 'ambiguity' in w.value.columns]
    assert len(frames) == 2
    proposed_frame = next(frame for frame in frames if len(frame) == 2)
    assert list(proposed_frame.columns) == ['Story', 'As a', 'want to', 'so that', 'acceptance criteria', 'ambiguity']
    assert list(proposed_frame['ambiguity']) == ['What time format?', 'When is clear allowed?']
    selectbox(app, 'ข้อเสนอที่ต้องการตรวจ').select('P-clear').run()
    button(app, 'รับเป็น draft').click().run()
    assert not app.exception
    saved = c.load_projects()[0]
    assert [s['title'] for s in saved['stories']] == ['Scan', 'Clear logs']
    assert saved['stories'][1]['open_questions'] == ['When is clear allowed?']
    assert saved['proposals'][0]['id'] == 'P-time'
    assert not saved['stories'][1]['reviewed']


def test_conversation_does_not_implicitly_target_first_story(tmp_path, monkeypatch):
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    snapshot = cap.load_snapshot(cap.list_snapshots()[0])
    project = c.new_project(snapshot)
    c.add_story(project)
    c.save_project(project)
    app = launch(tmp_path, monkeypatch)
    selectbox(app, 'Agent').select('Host agent / interactive').run()
    assert selectbox(app, 'หัวข้อสนทนา').value is None
    app.chat_input[0].set_value('Need separate goals: scan, set time and clear logs').run()
    assert not app.exception
    request = bridge.inbox()[0]['request']
    assert request['selected_story_id'] is None


def test_split_proposals_preserve_goals_and_require_explicit_acceptance(tmp_path, monkeypatch):
    from reqstudio import llm
    monkeypatch.setenv('FWLC_DATA_DIR', str(tmp_path))
    snapshot = cap.load_snapshot(cap.list_snapshots()[0])
    project = c.new_project(snapshot)
    original = c.add_story(project)
    c.update_story(original, {'title': 'Survey', 'role': 'surveyor', 'want': 'record surveys', 'benefit': 'keep evidence',
                             'acceptance_criteria': [{'text': 'Press records every SSID', 'test_intent': 'Compare file and scan', 'requires_hardware': True}]})
    old_ac_id = original['acceptance_criteria'][0]['id']
    project['messages'] = [{'id': 'TURN-goals', 'role': 'user', 'content': 'Scan and save, set time, clear logs, show counts'}]
    request = bridge.enqueue(project, 'TURN-goals', None)
    c.save_project(project)
    before = copy.deepcopy(project['stories'])
    proposals = []
    for i, goal in enumerate(['Scan and save', 'Set time', 'Clear logs', 'Show counts']):
        proposals.append({'operation': 'update' if i == 0 else 'create', 'story_id': original['id'] if i == 0 else None,
                          'base_revision': original['revision'] if i == 0 else None, 'title': goal, 'role': 'surveyor',
                          'want': goal, 'benefit': 'control surveys',
                          'acceptance_criteria': copy.deepcopy(original['acceptance_criteria']) if i == 0 else [{'id': '', 'text': goal, 'test_intent': 'Inspect result', 'requires_hardware': True}],
                          'open_questions': ['Clarify ' + goal], 'feasibility': 'unknown', 'feasibility_reason': '', 'capability_refs': []})
    saved = bridge.respond(project['project_id'], request['id'], {'reply': 'Four independent user goals', 'questions': [], 'proposals': proposals})
    assert saved['stories'] == before
    assert len(saved['proposals']) == 4
    context = llm.compact_context(saved, snapshot, None)
    assert len(context['unapplied_proposals']) == 4
    assert context['other_story_summaries'][0]['acceptance_criteria'][0]['id'] == old_ac_id
    for proposal in saved['proposals']:
        c.apply_proposal(saved, proposal, snapshot)
    assert len(saved['stories']) == 4
    assert saved['stories'][0]['id'] == original['id']
    assert saved['stories'][0]['acceptance_criteria'][0]['id'] == old_ac_id
    assert all(not story['reviewed'] for story in saved['stories'])
    assert [story['open_questions'] for story in saved['stories']] == [['Clarify ' + goal] for goal in ['Scan and save', 'Set time', 'Clear logs', 'Show counts']]

