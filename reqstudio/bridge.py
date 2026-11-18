"""Durable UI-to-host-agent requests. No model or unattended worker is started."""
from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from pathlib import Path

from . import contracts, llm
from .capabilities import utc_now


def context_signature(project, selected_id):
    selected = next((s for s in project['stories'] if s['id'] == selected_id), None)
    context = {k: project[k] for k in ('snapshot_id', 'board_id', 'constraints')}
    context['story'] = selected
    context['stories'] = project['stories']
    context['last_user_turn'] = next((m['id'] for m in reversed(project['messages']) if m['role'] == 'user'), None)
    return hashlib.sha256(json.dumps(context, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def enqueue(project, turn_id, selected_id, backend='host'):
    if backend not in {'host', 'background'}:
        raise ValueError('Unknown agent backend')
    if project.get('agent_request', {}).get('status') in {'pending', 'processing'}:
        raise ValueError('An agent request is already pending.')
    request = {'id': str(uuid.uuid4()), 'status': 'pending', 'created_at_utc': utc_now(),
               'turn_id': turn_id, 'selected_story_id': selected_id,
               'context_signature': context_signature(project, selected_id), 'backend': backend}
    project['agent_request'] = request
    return request


def inbox():
    return [{'project_id': p['project_id'], 'project_name': p['name'], 'request': p['agent_request'],
             'messages': p['messages'], 'stories': p['stories'], 'board_id': p['board_id'],
             'constraints': p['constraints'], 'snapshot_id': p['snapshot_id']}
            for p in contracts.load_projects() if p.get('agent_request', {}).get('status') == 'pending']


def respond(project_id, request_id, payload, producer='host-agent / interactive', worker_id=None):
    result = llm.parse_response(json.dumps(payload, ensure_ascii=False))
    project = json.loads(contracts.project_file(project_id).read_text(encoding='utf-8'))
    request = project.get('agent_request', {})
    valid = request.get('status') == 'pending' or (request.get('status') == 'processing' and worker_id and request.get('worker_id') == worker_id)
    if request.get('id') != request_id or not valid:
        raise ValueError('Request is cancelled, completed or no longer current.')
    if context_signature(project, request['selected_story_id']) != request['context_signature']:
        request.update(status='stale', completed_at_utc=utc_now())
        contracts.save_project(project)
        raise ValueError('Request context changed; user must submit a new request.')
    reply = result['reply']
    if result['questions']:
        reply += '\n\n' + '\n'.join('- ' + q for q in result['questions'])
    project['messages'].append({'id': 'TURN-' + uuid.uuid4().hex[:10], 'role': 'assistant', 'content': reply})
    affected = {x.get('story_id') for x in result['proposals'] if x.get('operation') == 'update'}
    superseded = [x for x in project['proposals'] if x.get('story_id') in affected and x.get('model', '').startswith(('host-agent', 'background-agent'))]
    if superseded:
        project.setdefault('proposal_history', []).extend([{**x, 'status': 'superseded', 'reason': 'New agent proposal'} for x in superseded])
        ids = {x['id'] for x in superseded}
        project['proposals'] = [x for x in project['proposals'] if x['id'] not in ids]
    for proposal in result['proposals']:
        proposal.update(id=uuid.uuid4().hex, source_turn_ids=[request['turn_id']], model=producer,
                        snapshot_id=project['snapshot_id'], board_id=project['board_id'])
        project['proposals'].append(proposal)
    request.update(status='completed', completed_at_utc=utc_now(), producer=producer)
    contracts.save_project(project)
    return project


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('inbox')
    response = sub.add_parser('respond')
    response.add_argument('--project', required=True)
    response.add_argument('--request', required=True)
    response.add_argument('--response', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'inbox':
        print(json.dumps(inbox(), ensure_ascii=False, indent=2))
    else:
        project = respond(args.project, args.request, json.loads(args.response.read_text(encoding='utf-8')))
        print(json.dumps({'project_id': project['project_id'], 'request_status': project['agent_request']['status']}))


if __name__ == '__main__':
    main()
