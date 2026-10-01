"""Probe the loopback deployment with real storage and client transport faults."""

import argparse
import asyncio
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx


async def verify(output):
    report = {'started_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'real_nginx_storage_with_client_transport_faults',
              'provider_faults_injected': False, 'client_deadline_seconds': 0.1,
              'real_model_requested': True, 'consultation_requests': 0,
              'model_call_count': None, 'checks': {}, 'cleanup': {},
              'limitations': ['The imposed timeout belongs to the HTTP client, not the model provider.',
                              'Disconnect is deliberate. UI timeout handling is verified separately.',
                              'No legal answer quality or provider outage rate is established.']}
    headers = {}
    session_ids = []
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8080', timeout=80) as client:
        async def baseline():
            response = await client.post('/api/v1/chat/send', headers=headers, json={'message': '取消任务'})
            response.raise_for_status()
            sid = response.json()['data']['session_id']
            session_ids.append(sid)
            history = await client.get(f'/api/v1/chat/history/{sid}', headers=headers)
            history.raise_for_status()
            return sid, history.json()['data']['messages']

        async def unchanged_history(sid, before):
            for _ in range(100):
                response = await client.get(f'/api/v1/chat/history/{sid}', headers=headers)
                if response.status_code == 200:
                    return response.json()['data']['messages'] == before
                if response.status_code != 409:
                    response.raise_for_status()
                await asyncio.sleep(0.2)
            return False

        try:
            invalid = await client.post('/api/v1/chat/stream',
                                       headers={'Authorization': 'Bearer invalid'}, json={'message': '取消任务'})
            report['checks']['invalid_token_rejected_before_stream'] = invalid.status_code == 401
            name = 'fault_' + uuid4().hex[:12]
            password = secrets.token_urlsafe(24)
            registered = await client.post('/api/v1/auth/register',
                                           json={'username': name, 'email': name + '@example.com', 'password': password})
            registered.raise_for_status()
            login = await client.post('/api/v1/auth/login', json={'login': name, 'password': password})
            login.raise_for_status()
            headers = {'Authorization': 'Bearer ' + login.json()['data']['access_token']}
            empty = await client.post('/api/v1/cases/search', headers=headers,
                                      json={'query': '劳动报酬', 'domain': 'labor_dispute', 'source_kind': 'official'})
            empty.raise_for_status()
            report['checks']['empty_official_case_index'] = empty.json()['data']['items'] == []

            message = '我想了解一般规则：建立劳动关系应当订立书面劳动合同吗？不涉及具体事件。'
            sid, before = await baseline()
            report['consultation_requests'] += 1
            timeout_seen = False
            try:
                async with client.stream('POST', '/api/v1/chat/stream', headers=headers,
                                         json={'message': message, 'session_id': sid},
                                         timeout=httpx.Timeout(10, read=0.1)) as response:
                    response.raise_for_status()
                    async for _ in response.aiter_lines():
                        pass
            except httpx.ReadTimeout:
                timeout_seen = True
            report['checks']['client_read_timeout_observed'] = timeout_seen
            report['checks']['timeout_preserves_history_and_releases_lease'] = await unchanged_history(sid, before)

            sid, before = await baseline()
            report['consultation_requests'] += 1
            saw_meta = False
            async with client.stream('POST', '/api/v1/chat/stream', headers=headers,
                                     json={'message': message, 'session_id': sid}) as response:
                response.raise_for_status()
                event = None
                async for line in response.aiter_lines():
                    if line.startswith('event: '):
                        event = line[7:]
                    elif event == 'meta' and line.startswith('data: '):
                        saw_meta = json.loads(line[6:])['session_id'] == sid
                        break
            report['checks']['disconnect_after_real_stream_meta'] = saw_meta
            report['checks']['disconnect_preserves_history_and_releases_lease'] = await unchanged_history(sid, before)
        except Exception as exc:
            report['error_type'] = type(exc).__name__
        finally:
            removed = []
            for sid in session_ids:
                try:
                    response = await client.delete(f'/api/v1/chat/history/{sid}', headers=headers)
                    removed.append(response.status_code == 200)
                except httpx.HTTPError:
                    removed.append(False)
            report['cleanup']['only_created_consultations_deleted'] = len(removed) == len(session_ids) and all(removed)
    report['passed'] = len(report['checks']) == 6 and all(report['checks'].values()) and all(report['cleanup'].values()) and 'error_type' not in report
    report['completed_at'] = datetime.now(timezone.utc).isoformat()
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'passed': report['passed'], 'checks': report['checks'], 'cleanup': report['cleanup']}))
    return report['passed']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-real-model', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    if not args.allow_real_model:
        raise SystemExit('This probe may consume model credits; --allow-real-model is required.')
    if args.output.exists() or not args.output.resolve().is_relative_to(root):
        raise SystemExit('Choose a new report path inside the workspace.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    return 0 if asyncio.run(verify(args.output)) else 1


if __name__ == '__main__':
    raise SystemExit(main())
