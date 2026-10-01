"""HTTP smoke test through Nginx: real storage/retrieval, zero model calls."""
import argparse
import asyncio
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import httpx


async def verify(base_url, output):
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'scope': 'deployed_http_smoke',
              'real_model_calls': 0, 'checks': {}, 'limitations': ['Does not establish legal answer quality or a clean environment by itself.']}
    checks = report['checks']
    async with httpx.AsyncClient(base_url=base_url, timeout=90) as client:
        async def account():
            name = 'deploy_' + uuid4().hex[:12]; password = secrets.token_urlsafe(24)
            result = await client.post('/api/v1/auth/register', json={'username':name,'email':name+'@example.com','password':password})
            result.raise_for_status()
            login = await client.post('/api/v1/auth/login', json={'login':name,'password':password}); login.raise_for_status()
            return {'Authorization':'Bearer '+login.json()['data']['access_token']}
        try:
            checks['health'] = (await client.get('/api/v1/health')).status_code == 200
            checks['spa_deep_link'] = 'LegalMind' in (await client.get('/documents')).text
            checks['production_docs_closed'] = (await client.get('/docs')).status_code in (404,200) and (await client.get('/openapi.json')).headers.get('content-type','').startswith('text/html')
            checks['anonymous_rejected'] = (await client.get('/api/v1/documents/templates')).status_code == 401
            checks['bad_token_rejected'] = (await client.get('/api/v1/documents/templates',headers={'Authorization':'Bearer invalid'})).status_code == 401
            owner, other = await account(), await account()
            result = await client.post('/api/v1/cases/search',headers=owner,json={'query':'劳动报酬','domain':'labor_dispute','top_k':5}); result.raise_for_status()
            cases = result.json()['data']['items']; checks['case_retrieval'] = bool(cases) and all(item['is_demo'] for item in cases)
            case = await client.get('/api/v1/cases/'+cases[0]['id'],headers=owner);case.raise_for_status()
            checks['case_detail_demo_boundary'] = case.json()['data']['is_synthetic']
            templates = (await client.get('/api/v1/documents/templates',headers=owner)).json()['data']['items']
            checks['three_templates'] = len(templates) == 3
            checks['downloads'] = True; checks['document_ownership'] = True
            for template in templates:
                generated = await client.post('/api/v1/documents/generate',headers=owner,json={'document_type':template['document_type'],'parameters':{field['name']:'用户提供的部署验收信息' for field in template['fields']},'use_references':False})
                generated.raise_for_status(); document_id=generated.json()['data']['document_id']
                for fmt in ('md','txt'):
                    response = await client.get(f'/api/v1/documents/{document_id}/download?format={fmt}',headers=owner)
                    checks['downloads'] &= response.status_code == 200 and '用户提供' in response.text
                checks['document_ownership'] &= (await client.get(f'/api/v1/documents/{document_id}/download',headers=other)).status_code == 404
            # Explicit cancellation is handled without extraction or generation.
            frames = ''
            async with client.stream('POST','/api/v1/chat/stream',headers=owner,json={'message':'取消任务','document_type':'general_contract','task_action':'cancel'}) as response:
                response.raise_for_status()
                async for data in response.aiter_text(): frames += data
            checks['sse_proxy_and_redis_commit'] = all(f'event: {name}' in frames for name in ('meta','content','sources','done')) and '"success":true' in frames
            meta = next(json.loads(line[6:]) for line in frames.splitlines() if line.startswith('data: ') and '"session_id"' in line)
            sid = meta['session_id']
            history = await client.get(f'/api/v1/chat/history/{sid}',headers=owner);history.raise_for_status()
            checks['server_history'] = len(history.json()['data']['messages']) == 2
            checks['session_ownership'] = (await client.get(f'/api/v1/chat/history/{sid}',headers=other)).status_code == 404
            checks['delete_history'] = (await client.delete(f'/api/v1/chat/history/{sid}',headers=owner)).status_code == 200
        except Exception as exc:
            report['error_type'] = type(exc).__name__
    report['passed'] = bool(checks) and all(checks.values()) and 'error_type' not in report
    report['completed_at'] = datetime.now(timezone.utc).isoformat()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream: json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps({'passed':report['passed'],'checks':checks},ensure_ascii=False))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base-url',default='http://127.0.0.1:8080');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise SystemExit('Choose a new report path')
    return 0 if asyncio.run(verify(args.base_url,args.output))['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
