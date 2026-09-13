"""Shared enum values used by storage, validation, retrieval, and APIs."""

from enum import StrEnum


class LegalDomain(StrEnum):
    MARRIAGE_FAMILY = "marriage_family"
    LABOR_DISPUTE = "labor_dispute"
    TRAFFIC_ACCIDENT = "traffic_accident"
    CONTRACT_DISPUTE = "contract_dispute"


class SourceKind(StrEnum):
    DEMO = "demo"
    OFFICIAL = "official"
    PUBLIC_REFERENCE = "public_reference"


class SourceType(StrEnum):
    CASE = "case"
    LEGAL_PROVISION = "legal_provision"


class LegalStatus(StrEnum):
    EFFECTIVE = "effective"
    AMENDED = "amended"
    REPEALED = "repealed"
    UNKNOWN = "unknown"


class ImportStatus(StrEnum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"
