"""Build a fully isolated database and real embedding index for benchmark runs."""

import hashlib
import json
from pathlib import Path

from app.core.config import BACKEND_DIR, Settings
from app.db.base import Base
from app.db.session import Database
from app.evaluation.dataset import catalog_entries, sha256
from app.rag.embeddings import create_embedding_client
from app.rag.importer import import_cases, load_case_records
from app.rag.indexer import index_cases
from app.rag.legal_catalog import import_catalog
from app.rag.retriever import HybridCaseRetriever
from app.rag.vector_store import ChromaVectorStore


def prepare(workspace: Path):
    workspace = workspace.resolve()
    allowed = (BACKEND_DIR.parent / 'tmp').resolve()
    if not workspace.is_relative_to(allowed):
        raise ValueError('Evaluation workspace must be inside the project tmp directory')
    workspace.mkdir(parents=True, exist_ok=True)
    settings = Settings(environment='test', log_level='WARNING', embedding_backend='sentence_transformers',
                        database_url=f"sqlite:///{(workspace/'evaluation.db').as_posix()}", chroma_persist_directory=workspace/'chroma')
    database = Database(settings.database_url.get_secret_value())
    Base.metadata.create_all(database.engine)
    import_cases(database, load_case_records(BACKEND_DIR/'data/demo/cases.jsonl'))
    import_catalog(database, catalog_entries())
    embedding = create_embedding_client(settings)
    store = ChromaVectorStore(settings.chroma_persist_directory, settings.chroma_collection_name, embedding)
    summary = index_cases(database, store, embedding)
    if summary.failed or store.count() != 64:
        database.dispose()
        raise RuntimeError('Isolated case index could not be built completely')
    return settings, database, embedding, store, HybridCaseRetriever(database, store, embedding)


def provenance(settings: Settings) -> dict:
    files = sorted(p for folder in ('app/agents','app/rag','app/evaluation','app/services','scripts')
                   for p in (BACKEND_DIR/folder).glob('*.py'))
    hashes = {p.relative_to(BACKEND_DIR).as_posix(): sha256(p) for p in files}
    return {'implementation_sha256': hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),
            'implementation_files':hashes,'embedding_model':settings.embedding_model_name,
            'embedding_revision':settings.embedding_model_revision,'embedding_dimension':settings.embedding_dimension,
            'embedding_device':settings.embedding_device,'llm_model':settings.deepseek_model,
            'llm_temperature':settings.llm_temperature,'llm_max_tokens':settings.llm_max_tokens,
            'query_manifest_sha256':sha256(BACKEND_DIR/'data/evaluation/rag-v1/manifest.json'),
            'isolation':'fresh SQLite and Chroma under tmp; no default database or vector writes'}
