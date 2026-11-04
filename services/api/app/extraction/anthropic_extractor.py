import base64
import json
import logging
import time

import anthropic

from .base import (
    ExtractionError,
    ExtractionNotConfigured,
    ExtractionResult,
    FieldResult,
    ProviderCandidate,
)
from .prompt import PROMPT_VERSION, SYSTEM_PROMPT, USER_PROMPT
from .schema import EXTRACTION_SCHEMA, FIELD_KEYS
from .settings import ExtractionSettings

log = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_TOKENS = 16000


class AnthropicExtractor:
    def __init__(self, settings: ExtractionSettings, client: anthropic.Anthropic | None = None):
        self._settings = settings
        if client is None:
            if settings.anthropic_api_key is None:
                raise ExtractionNotConfigured("ANTHROPIC_API_KEY is not set")
            client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key.get_secret_value(),
                timeout=settings.extraction_timeout_s,
                max_retries=0,
            )
        self._client = client

    def extract(self, pdf_bytes: bytes, filename: str) -> ExtractionResult:
        s = self._settings
        start = time.monotonic()
        try:
            with self._client.beta.messages.stream(
                model=s.extraction_model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                thinking={"type": "adaptive"},
                betas=[FALLBACK_BETA],
                fallbacks="default",
                output_config={
                    "effort": "high",
                    "format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA},
                },
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": base64.standard_b64encode(pdf_bytes).decode("ascii"),
                                },
                            },
                            {"type": "text", "text": USER_PROMPT},
                        ],
                    }
                ],
                timeout=s.extraction_timeout_s,
            ) as stream:
                message = stream.get_final_message()
        except anthropic.APITimeoutError as e:
            raise ExtractionError("extraction timed out") from e
        except anthropic.APIError as e:
            log.warning("anthropic api error: %s", type(e).__name__)
            raise ExtractionError("extraction provider error") from e
        latency_ms = int((time.monotonic() - start) * 1000)

        if message.stop_reason == "refusal":
            raise ExtractionError("extraction request was declined by the model")
        if message.stop_reason == "max_tokens":
            raise ExtractionError("extraction output was truncated")

        text = next((b.text for b in message.content if b.type == "text"), None)
        if text is None:
            raise ExtractionError("extraction returned no content")
        try:
            data = json.loads(text)
            return self._to_result(data, message, latency_ms)
        except (ValueError, TypeError, KeyError) as e:
            raise ExtractionError("extraction returned malformed output") from e

    def _to_result(self, data: dict, message, latency_ms: int) -> ExtractionResult:
        fields = {k: FieldResult(**(data.get(k) or {})) for k in FIELD_KEYS}
        candidates = [
            ProviderCandidate(
                name=c["name"],
                role=c.get("role") or None,
                npi=c.get("npi") or None,
                page=c.get("page") or None,
            )
            for c in data.get("provider_candidates") or []
        ]
        usage = message.usage
        return ExtractionResult(
            provider="anthropic",
            model=getattr(message, "model", None) or self._settings.extraction_model,
            prompt_version=PROMPT_VERSION,
            latency_ms=latency_ms,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            fields=fields,
            provider_candidates=candidates,
            notes=data.get("notes") or None,
        )
