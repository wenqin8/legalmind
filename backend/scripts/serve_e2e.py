"""Loopback-only isolated browser fixture; never loads the developer .env."""
import argparse
import asyncio
import json
import secrets
from pathlib import Path
import uvicorn
from app.core.config import Settings, BACKEND_DIR
from app.db.base import Base
from app.db.session import Database
from app.main import create_app
from app.rag.embeddings import DeterministicHashEmbedding
from app.rag.importer import import_cases, load_case_records
from app.rag.indexer import index_cases
from app.rag.vector_store import ChromaVectorStore
from app.rag.retriever import HybridCaseRetriever
from tests.agent_helpers import AgentLLM
from tests.session_store import FakeSessionStore


class BrowserModel(AgentLLM):
    async def stream(self, messages):
        data = json.loads(messages[1].content)
        query = data['query']
        yield '结论\n可按演示场景整理已有材料[S1]。\n\n'
        if '超时演示' in query:
            await asyncio.sleep(30)
        elif '断流演示' in query:
            await asyncio.sleep(3)
        else:
            await asyncio.sleep(0.1)
        yield '风险\n当前只有演示资料，法律依据不足。\n\n下一步\n请核对原始材料。'


class BrowserRetriever(HybridCaseRetriever):
    def search(self, query, **kwargs):
        if query == '无匹配演示': return []
        return super().search(query, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8011)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not root.is_relative_to((BACKEND_DIR.parent / 'tmp').resolve()) or root.exists():
        raise ValueError('A fresh workspace inside project tmp is required')
    root.mkdir(parents=True)
    settings = Settings(_env_file=None, environment='test', llm_backend='fake', embedding_backend='fake',
        database_url=f'sqlite:///{(root / "e2e.db").as_posix()}', jwt_secret_key=secrets.token_urlsafe(48),
        chroma_persist_directory=root / 'chroma', cors_origins=('http://127.0.0.1:5173',),
        deepseek_timeout_seconds=1.5, log_level='WARNING')
    database = Database(settings.database_url.get_secret_value())
    Base.metadata.create_all(database.engine)
    import_cases(database, load_case_records(BACKEND_DIR / 'data/demo/cases.jsonl'))
    embedding = DeterministicHashEmbedding()
    vectors = ChromaVectorStore(root / 'chroma', settings.chroma_collection_name, embedding)
    summary = index_cases(database, vectors, embedding)
    if summary.failed or vectors.count() != 64: raise RuntimeError('Fixture indexing failed')
    app = create_app(settings, database=database, llm_client=BrowserModel(), embedding_client=embedding,
        vector_store=vectors, case_retriever=BrowserRetriever(database, vectors, embedding), session_store=FakeSessionStore())
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False, log_level='warning')


if __name__ == '__main__': main()
