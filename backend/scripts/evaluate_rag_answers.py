"""Forty frozen scenarios, one real-model run, isolated HTTP/Redis state and full traces."""

import argparse
import asyncio
import json
import secrets
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
import uvicorn
from anyio import fail_after
from sqlalchemy import select

from app.core.config import BACKEND_DIR
from app.db.models import LegalProvision
from app.evaluation.answers import check_turn
from app.evaluation.dataset import BENCHMARK_DIR, load_queries
from app.evaluation.environment import prepare, provenance
from app.evaluation.metrics import percentile
from app.llm.base import LLMClient
from app.llm.factory import create_llm_client
from app.main import create_app


class TraceLLM(LLMClient):
    def __init__(self, client):
        self.client=client
        self.calls=[]

    def begin(self,messages):
        item={'task':messages[0].content.split('\n')[0], 'input':json.loads(messages[1].content), 'output':''}
        self.calls.append(item)
        return item

    async def complete(self,messages):
        item=self.begin(messages); start=time.perf_counter()
        try:
            item['output']=await self.client.complete(messages)
            return item['output']
        except BaseException as exc:
            item['error_type']=type(exc).__name__;raise
        finally:item['elapsed_seconds']=round(time.perf_counter()-start,3)

    async def stream(self,messages):
        item=self.begin(messages);start=time.perf_counter()
        stream=self.client.stream(messages)
        try:
            async for part in stream:
                item['output']+=part
                yield part
        except BaseException as exc:
            item['error_type']=type(exc).__name__;raise
        finally:
            await stream.aclose()
            item['elapsed_seconds']=round(time.perf_counter()-start,3)

    async def aclose(self):await self.client.aclose()


def summarize(report):
    turns=[t for scenario in report['scenarios'] for t in scenario['turns']]
    ok=[t for t in turns if t.get('status')==200]
    answers=[t for t in turns if t['expected']['expected']=='answer']
    negatives=[t for t in turns if t['expected']['expected']=='insufficient']
    def rate(items,predicate):
        return {'value':sum(predicate(t) for t in items)/len(items) if items else None,'denominator':len(items)}
    report['summary']={'scenarios_attempted':len(report['scenarios']), 'turns_planned':len(turns), 'successful_http_turns':len(ok),
        'model_calls':sum(len(t.get('model_trace',[])) for t in turns),
        'scenario_structural_passes':sum(all(t.get('evaluation',{}).get('structural_passed',False) for t in s['turns']) for s in report['scenarios']),
        'behavior_match_including_errors':rate(turns,lambda t:t.get('evaluation',{}).get('checks',{}).get('expected_behavior',False)),
        'answer_behavior_rate':rate(answers,lambda t:t.get('evaluation',{}).get('observed_behavior')=='answer'),
        'strict_insufficient_rate':rate(negatives,lambda t:t.get('evaluation',{}).get('observed_behavior')=='insufficient'),
        'safe_nonanswer_rate':rate(negatives,lambda t:t.get('evaluation',{}).get('observed_behavior') in ('insufficient','clarify')),
        'http_latency_seconds_p50':percentile([t['elapsed_seconds'] for t in ok],.5),
        'http_latency_seconds_p95':percentile([t['elapsed_seconds'] for t in ok],.95),
        'semantic_quality_passed':None,'expert_review':'not performed'}


async def evaluate(output: Path):
    query_by_id={q.id:q for q in load_queries()}
    scenarios=[json.loads(line) for line in (BENCHMARK_DIR/'scenarios.jsonl').read_text(encoding='utf-8').splitlines()]
    workspace=BACKEND_DIR.parent/'tmp'/('rag-answers-'+uuid4().hex)
    settings,database,embedding,store,retriever=await asyncio.to_thread(prepare,workspace)
    settings=settings.model_copy(update={'llm_backend':'deepseek'})
    llm=TraceLLM(create_llm_client(settings))
    app=create_app(settings,database=database,embedding_client=embedding,vector_store=store,case_retriever=retriever,llm_client=llm)
    known={}
    with database.session() as session:
        for row in session.scalars(select(LegalProvision)):
            known[str(row.id)]={'record_id':row.record_id,'title':row.regulation_name,'reference_number':row.article_number,
                'source_url':row.source_url,**{k:row.verification.get(k) for k in ('version','original_text','effective_from','effective_until','verified_at','status_as_of')}}
    report={'started_at':datetime.now(timezone.utc).isoformat(),'configuration':provenance(settings),'transport':'real_loopback_http',
        'model_attempts_per_turn':1,'complete':False,'scenarios':[], 'cleanup':{},'annotation_status':'agent_draft_pending_expert'}
    def save():
        summarize(report)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128);listener.setblocking(False)
    server=uvicorn.Server(uvicorn.Config(app,lifespan='off',log_level='critical',access_log=False))
    server_task=asyncio.create_task(server.serve(sockets=[listener]))
    user_id=None
    try:
        await app.state.session_store.client.ping()
        with fail_after(15):
            while not server.started:
                if server_task.done():await server_task
                await asyncio.sleep(.02)
        async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{listener.getsockname()[1]}',timeout=80) as client:
            username='eval_'+uuid4().hex[:16];password=secrets.token_urlsafe(24)
            registration=await client.post('/api/v1/auth/register',json={'username':username,'email':username+'@example.com','password':password})
            registration.raise_for_status();user_id=registration.json()['data']['id']
            token=None; token_at=0
            for scenario in scenarios:
                # Refresh authentication before expiry; model generations are never retried.
                if time.monotonic()-token_at>2400:
                    login=await client.post('/api/v1/auth/login',json={'login':username,'password':password})
                    login.raise_for_status();token=login.json()['data']['access_token'];token_at=time.monotonic()
                headers={'Authorization':'Bearer '+token}
                entry={k:v for k,v in scenario.items() if k!='turns'};entry['turns']=[]
                sid=None; messages={}; previous_failed=False
                query=query_by_id[scenario['query_id']]
                for expected in scenario['turns']:
                    if previous_failed:
                        entry['turns'].append({'expected':expected,'status':None,'error':'dependency_failed','model_trace':[]})
                        continue
                    begin=len(llm.calls);start=time.perf_counter()
                    payload={'message':expected['message']}
                    if sid:payload['session_id']=sid
                    turn={'expected':expected}
                    try:
                        response=await client.post('/api/v1/chat/send',headers=headers,json=payload)
                        turn.update(status=response.status_code,elapsed_seconds=round(time.perf_counter()-start,3),model_trace=llm.calls[begin:])
                        body=response.json()
                        if response.status_code==200:
                            data=body['data'];sid=data['session_id'];turn['response']=data
                            history=await client.get(f'/api/v1/chat/history/{sid}',headers=headers)
                            history.raise_for_status()
                            for message in history.json()['data']['messages']:
                                if message['role']=='user':messages[message['turn_id']]=message['content']
                            turn['message_provenance']=messages.copy()
                            turn['evaluation']=check_turn(data,expected,known,turn['model_trace'],{k:v.grade for k,v in query.relevance.items()},messages)
                        else:
                            turn['error']=body.get('error',{}).get('code','http_error');previous_failed=True
                    except Exception as exc:
                        turn.update(status=turn.get('status'),error=type(exc).__name__,elapsed_seconds=round(time.perf_counter()-start,3),model_trace=llm.calls[begin:])
                        previous_failed=True
                    entry['turns'].append(turn)
                report['scenarios'].append(entry);save()
                print(json.dumps({'scenario':scenario['id'],'completed':len(report['scenarios']),'statuses':[t.get('status') for t in entry['turns']],
                    'behaviors':[t.get('evaluation',{}).get('observed_behavior') for t in entry['turns']]}),flush=True)
            report['complete']=len(report['scenarios'])==40
    except Exception as exc:
        report['infrastructure_error']=type(exc).__name__
    finally:
        server.should_exit=True
        with fail_after(15):await server_task
        listener.close()
        try:
            if user_id:
                redis=app.state.session_store.client
                keys=[key async for key in redis.scan_iter(match=f'conversation:{user_id}:*')]
                if keys:await redis.delete(*keys)
                report['cleanup']['synthetic_redis_keys_removed']=not [key async for key in redis.scan_iter(match=f'conversation:{user_id}:*')]
        except Exception as exc:report['cleanup']['error']=type(exc).__name__
        await llm.aclose();await app.state.session_store.aclose();database.dispose()
        report['completed_at']=datetime.now(timezone.utc).isoformat();save()
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Choose a new output path; prior raw runs must be preserved')
    report=asyncio.run(evaluate(args.output))
    print(json.dumps({'complete':report['complete'],'summary':report['summary'],'cleanup':report['cleanup']},ensure_ascii=False))
    return 0 if report['complete'] and report['cleanup'].get('synthetic_redis_keys_removed') else 2


if __name__=='__main__':raise SystemExit(main())
