"""Deterministic draft rendering; source selection never invents document facts."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.agents.evidence import retrieve_evidence, select_evidence, source_summary
from app.core.errors import AppError, DatabaseUnavailableError, ResourceNotFoundError
from app.db.models import GeneratedDocument
from app.db.session import Database
from app.llm.base import LLMClient
from app.rag.retriever import HybridCaseRetriever
from app.schemas.chat import CHAT_DISCLAIMER
from app.schemas.documents import DRAFT_WARNING, TEMPLATES, DocumentData, DocumentRequest


def validate_parameters(payload: DocumentRequest) -> dict[str, str]:
    template = TEMPLATES[payload.document_type]
    allowed = {field.name for field in template.fields}
    if set(payload.parameters) - allowed:
        raise AppError(status_code=422, code="VALIDATION_ERROR", message="文书包含未知字段")
    values = {name: value.strip() for name, value in payload.parameters.items()}
    if any(len(values.get(field.name, "")) > field.max_length for field in template.fields):
        raise AppError(status_code=422, code="VALIDATION_ERROR", message="文书字段超过长度限制")
    missing = [{"name": field.name, "message": f"请填写{field.label}"} for field in template.fields if not values.get(field.name)]
    if missing:
        raise AppError(status_code=422, code="DOCUMENT_FIELDS_MISSING", message="请补充文书必要信息", details={"fields": missing})
    return values


def markdown_literal(value: str) -> str:
    # Preserve user text without allowing it to create active Markdown/HTML content.
    return re.sub(r"([\\`*_{}\[\]<>()#!|~>])", r"\\\1", value)


@dataclass
class PreparedDocument:
    data: DocumentData
    parameters: dict[str, str]
    additional_instructions: str

    def row(self, user_id: UUID) -> GeneratedDocument:
        return GeneratedDocument(
            id=self.data.document_id, user_id=user_id, document_type=self.data.document_type,
            title=self.data.title, content=self.data.content, parameters=self.parameters,
            additional_instructions=self.additional_instructions,
            sources=[s.model_dump(mode="json") for s in self.data.sources],
            created_at=self.data.created_at, updated_at=self.data.created_at,
        )


async def prepare_document(payload: DocumentRequest, database: Database, retriever: HybridCaseRetriever, llm: LLMClient) -> PreparedDocument:
    parameters = validate_parameters(payload)
    template = TEMPLATES[payload.document_type]
    parts = [DRAFT_WARNING, f"# {template.name}"]
    parts.extend(f"## {field.label}\n{markdown_literal(parameters[field.name])}" for field in template.fields)
    if payload.additional_instructions:
        parts.append("## 用户补充说明\n" + markdown_literal(payload.additional_instructions))
    sources = []
    warnings = [DRAFT_WARNING, CHAT_DISCLAIMER]
    if payload.use_references:
        query = "\n".join(parameters.values())[:1000]
        evidence = await retrieve_evidence(query, database, retriever)
        selected = await select_evidence(query, [], evidence, llm)
        sources = [e.source for e in selected]
        if sources:
            parts.append("## 演示参考材料（不作为法律依据）\n" + source_summary(sources))
        else:
            warnings.append("没有可确认相关的参考资料；文书仅按用户提供的信息填入模板。")
    parts.append("## 人工复核\n请核对填写内容、证据和适用要求；本草稿未核验法律依据，不自动添加签名或日期。")
    data = DocumentData(document_id=uuid4(), document_type=payload.document_type, title=template.name,
                        content="\n\n".join(parts), sources=sources, warnings=warnings, created_at=datetime.now(timezone.utc))
    return PreparedDocument(data, parameters, payload.additional_instructions)


def save_document(prepared: PreparedDocument, user_id: UUID, database: Database) -> None:
    try:
        with database.session() as session, session.begin():
            session.add(prepared.row(user_id))
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc


def read_document(document_id: UUID, user_id: UUID, database: Database) -> GeneratedDocument:
    try:
        with database.session() as session:
            document = session.scalar(select(GeneratedDocument).where(GeneratedDocument.id == document_id, GeneratedDocument.user_id == user_id))
            if document is None:
                raise ResourceNotFoundError()
            return document
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError() from exc


def plain_text(content: str) -> str:
    # Our renderer only emits headings and escaped literal fields, not arbitrary Markdown.
    content = re.sub(r"(?m)^#{1,2} ", "", content)
    return re.sub(r"\\([\\`*_{}\[\]<>()#!|~>])", r"\1", content)
