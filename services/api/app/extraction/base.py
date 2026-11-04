from typing import Protocol

from pydantic import BaseModel

FIELD_NAMES = (
    "patient_first_name",
    "patient_last_name",
    "patient_dob",
    "provider_name",
    "provider_npi",
)


class ExtractionError(Exception):
    """Timeout or API failure. Callers map this to HTTP 502 (retryable)."""


class ExtractionNotConfigured(Exception):
    """Provider unavailable (e.g. no API key). Callers map this to HTTP 503."""


class FieldResult(BaseModel):
    value: str | None = None
    evidence: str | None = None
    page: int | None = None


class ProviderCandidate(BaseModel):
    name: str
    role: str | None = None
    npi: str | None = None
    page: int | None = None


class ExtractionResult(BaseModel):
    provider: str
    model: str
    prompt_version: str
    latency_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    fields: dict[str, FieldResult]
    provider_candidates: list[ProviderCandidate] = []
    notes: str | None = None


class Extractor(Protocol):
    def extract(self, pdf_bytes: bytes, filename: str) -> ExtractionResult: ...
