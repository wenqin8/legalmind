"""Real HTTP/Redis/DeepSeek smoke, using synthetic inputs and an isolated SQLite DB."""

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
from alembic import command
from alembic.config import Config
from sqlalchemy import update

from app.core.config import BACKEND_DIR, Settings
from app.db.models import Case
from app.main import create_app
from app.llm.base import LLMClient
from app.rag.importer import import_cases, load_case_records
from app.rag.legal_catalog import load_catalog, import_catalog
from scripts.verify_postgres_week2 import _alembic_url


async def verify() -> dict:
    workspace = BACKEND_DIR.parent / 'tmp' / ('legal-multiturn-' + uuid4().hex)
    workspace.mkdir(parents=True)
    settings = Settings(environment='test', log_level='WARNING', llm_backend='deepseek', database_url=f"sqlite:///{(workspace / 'smoke.db').as_posix()}")
    config = Config(str(BACKEND_DIR / 'alembic.ini'))
    with _alembic_url(settings.database_url.get_secret_value()):
        command.upgrade(config, 'head')
    app = create_app(settings)
    trace = []
    underlying = app.state.llm_client
    class TraceLLM(LLMClient):
        async def complete(self, messages):
            item = {'task':messages[0].content.split('\n')[0], 'synthetic_input':messages[1].content}
            trace.append(item)
            try:
                item['output'] = await underlying.complete(messages)
                return item['output']
            except BaseException as exc:
                item['error_type'] = type(exc).__name__
                raise
        async def stream(self, messages):
            item = {'task':'TASK:QA', 'synthetic_input':messages[1].content, 'output':''}
            trace.append(item)
            stream = underlying.stream(messages)
            try:
                async for part in stream:
                    item['output'] += part
                    yield part
            finally:
                await stream.aclose()
        async def aclose(self):
            await underlying.aclose()
    app.state.llm_client = TraceLLM()
    import_cases(app.state.database, load_case_records(BACKEND_DIR / 'data/demo/cases.jsonl'))
    import_catalog(app.state.database, load_catalog(BACKEND_DIR / 'data/legal/verified_provisions.jsonl'))
    # Existing local case vectors are read only; IDs are frozen and match the imported cases.
    with app.state.database.session() as session, session.begin():
        session.execute(update(Case).values(import_status='indexed'))
    report = {'checked_at':datetime.now(timezone.utc).isoformat(), 'transport':'real_loopback_http', 'model':settings.deepseek_model, 'checks':{}, 'synthetic_responses':{}}
    def check(name, value):
        report['checks'][name] = bool(value)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0)); listener.listen(128); listener.setblocking(False)
    server = uvicorn.Server(uvicorn.Config(app, lifespan='off', log_level='critical', access_log=False))
    server_task = asyncio.create_task(server.serve(sockets=[listener]))
    user_id = None
    try:
        check('redis_ping', await app.state.session_store.client.ping())
        with fail_after(15):
            while not server.started:
                if server_task.done(): await server_task
                await asyncio.sleep(.02)
        async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{listener.getsockname()[1]}', timeout=85) as client:
            username = 'law_' + uuid4().hex[:12]
            password = secrets.token_urlsafe(24)
            registered = await client.post('/api/v1/auth/register', json={'username':username,'email':username+'@example.com','password':password})
            registered.raise_for_status()
            user_id = registered.json()['data']['id']
            login = await client.post('/api/v1/auth/login',json={'login':username,'password':password})
            login.raise_for_status()
            headers = {'Authorization':'Bearer '+login.json()['data']['access_token']}
            async def send(name, message, **extra):
                started = time.monotonic()
                result = await client.post('/api/v1/chat/send',headers=headers,json={'message':message,**extra})
                if result.status_code != 200:
                    report['synthetic_responses'][name] = {'status':result.status_code,'code':result.json().get('error',{}).get('code')}
                    check(name,False)
                    return None
                data = result.json()['data']
                report['synthetic_responses'][name] = {'elapsed_seconds':round(time.monotonic()-started,2), **data}
                print(json.dumps({'step':name,'phase':data.get('task',{}).get('phase') if data.get('task') else None,'sources':len(data['sources'])}),flush=True)
                return data

            first = await send('labor_collect', '合成咨询：公司拖欠我的工资，我该如何准备材料申请仲裁？')
            check('labor_collect',first and first.get('task') and 'event_date' in first['missing_fields'])
            if first:
                second = await send('labor_followup','关键事件发生于2025年6月1日：公司拖欠当月工资。我与公司为劳动关系，2024年3月1日入职，已经签署书面劳动合同；我保存了合同、考勤和工资转账记录，仍在职。',session_id=first['session_id'])
                # Conflicting expanded facts must be confirmed explicitly.
                if second and second.get('task') and second['task']['phase']=='conflict':
                    second = await send('labor_accept','确认修改',session_id=first['session_id'])
                check('labor_legal_sources',second and any(s['source_type']=='legal_provision' for s in second['sources']))
            scenarios = {
                'marriage':'合成咨询：2025年6月1日协议离婚，双方亲生子女8岁随母亲生活，离婚协议约定父亲每月支付抚养费但尚未支付。父母子女身份没有争议，已有离婚证、书面离婚协议和转账记录。该如何整理追索抚养费的材料？',
                'traffic':'合成咨询：2025年6月1日机动车撞伤行人。交警已出具事故认定书，机动车承担全部责任，车辆有交强险和商业保险。已有认定书、医疗票据和保险单，行人正在治疗，未确定伤残。赔偿保险材料如何整理？',
                'contract':'合成咨询：2025年6月1日双方签订普通货物买卖合同，约定当月10日交货。买方已按约付款，卖方至今没有交货，也未提出不可抗力。双方均有相应民事行为能力，合同无已知效力争议。已有书面合同、付款和催告记录。可从哪些方面分析违约责任？',
            }
            for name,message in scenarios.items():
                data=await send(name,message)
                check(name+'_event_result',data and (any(s['source_type']=='legal_provision' for s in data['sources']) or (data.get('task') and data['task']['phase']=='collecting' and 1<=len(data['task']['questions'])<=3)))
            general_questions = {
                'marriage':'我想了解离婚后子女抚养费的一般现行规定，不涉及具体事件，不需要计算金额。请引用本地核验的官方条文说明一般原则。',
                'traffic':'我想了解机动车交通事故保险赔偿顺序的一般现行规定，不涉及具体事件，不需要计算责任比例和金额。请引用本地核验的官方条文说明一般原则。',
                'contract':'我想了解普通合同不履行义务时违约责任的一般现行规定，不涉及具体事件。请引用本地核验的官方条文说明一般原则。',
            }
            for name,message in general_questions.items():
                data=await send(name+'_general',message)
                check(name+'_legal_sources',data and any(s['source_type']=='legal_provision' for s in data['sources']))
            doc = await send('document_collect','帮我起草一份民事起诉状。原告是合成甲，被告是合成乙。')
            check('document_collect',doc and doc.get('task') and set(doc['task']['fields']) >= {'plaintiff','defendant'} and doc['document_id'] is None)
            if doc:
                sid=doc['session_id']
                review=await send('document_review','诉讼请求是返还货款1000元。事实与理由是合成甲已经付款但合成乙未交货。受理法院填写测试市人民法院。',session_id=sid)
                check('document_review',review and review.get('task') and review['task']['phase']=='review' and review['document_id'] is None)
                if review and review.get('task') and review['task']['phase']=='review':
                    generated=await send('document_confirm','确认生成',session_id=sid,task_action='confirm',task_revision=review['task']['revision'])
                    check('document_confirm',generated and generated['document_id'])
                    if generated and generated['document_id']:
                        result=await client.get(f"/api/v1/documents/{generated['document_id']}/download?format=txt",headers=headers)
                        check('document_download',result.status_code==200 and '1000元' in result.text)
    except Exception as exc:
        report['error_type']=type(exc).__name__
        check('unexpected_error',False)
    finally:
        server.should_exit=True
        with fail_after(15): await server_task
        listener.close()
        if user_id:
            redis=app.state.session_store.client
            keys=[key async for key in redis.scan_iter(match=f'conversation:{user_id}:*')]
            if keys: await redis.delete(*keys)
            check('test_redis_keys_removed',not [key async for key in redis.scan_iter(match=f'conversation:{user_id}:*')])
        await app.state.llm_client.aclose()
        await app.state.session_store.aclose()
        app.state.database.dispose()
        (workspace / 'synthetic-model-trace.json').write_text(json.dumps(trace,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'diagnostic_trace':str(workspace / 'synthetic-model-trace.json')}),flush=True)
    report['passed']=all(report['checks'].values()) and len(report['checks'])>=10
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=asyncio.run(verify())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='synthetic_responses'},ensure_ascii=False,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
