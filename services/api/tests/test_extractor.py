import pytest

from app.extraction import FIELD_NAMES, ExtractionNotConfigured, get_extractor
from app.extraction.fake import FakeExtractor
from app.extraction.settings import ExtractionSettings


def test_ac_m3_1_fake_extractor_returns_benchmark_shape():
    r = FakeExtractor().extract(b"%PDF-", "x.pdf")
    assert set(r.fields) == set(FIELD_NAMES)
    assert r.fields["patient_first_name"].value == "Marie"
    assert r.fields["provider_npi"].value == "9182734556"
    for f in r.fields.values():
        assert f.evidence and f.page == 1
    assert [c.name for c in r.provider_candidates][-1] == "Gregory House MD"
    assert r.provider_candidates[-1].page == 2


def test_fake_provider_refused_in_production():
    s = ExtractionSettings(extraction_provider="fake", env="production", _env_file=None)
    with pytest.raises(ExtractionNotConfigured):
        get_extractor(s)


def test_fake_provider_allowed_in_dev():
    s = ExtractionSettings(extraction_provider="fake", env="development", _env_file=None)
    assert isinstance(get_extractor(s), FakeExtractor)


# --- AnthropicExtractor with a mocked client -------------------------------------------------
import base64  # noqa: E402
import json  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import anthropic  # noqa: E402
import httpx2  # noqa: E402

from app.extraction import ExtractionError  # noqa: E402
from app.extraction.anthropic_extractor import AnthropicExtractor  # noqa: E402
from app.extraction.schema import EXTRACTION_SCHEMA  # noqa: E402

_PAYLOAD = {
    "patient_first_name": {"value": "Ann", "evidence": "Ann Lee", "page": 1},
    "patient_last_name": {"value": "Lee", "evidence": "Ann Lee", "page": 1},
    "patient_dob": {"value": None, "evidence": None, "page": None},
    "provider_name": {"value": "Dr X", "evidence": "Prescriber Dr X", "page": 2},
    "provider_npi": {"value": None, "evidence": None, "page": None},
    "provider_candidates": [{"name": "Dr X", "role": "prescriber", "npi": None, "page": 2}],
    "notes": None,
}


class _Stream:
    def __init__(self, message=None, exc=None):
        self._m, self._e = message, exc

    def __enter__(self):
        if self._e:
            raise self._e
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self._m


class _Client:
    def __init__(self, message=None, exc=None):
        self.calls = []
        self._stream = _Stream(message, exc)
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._record))

    def _record(self, **kw):
        self.calls.append(kw)
        return self._stream


def _msg(text=None, stop="end_turn"):
    content = [SimpleNamespace(type="text", text=text)] if text is not None else []
    return SimpleNamespace(
        content=content,
        stop_reason=stop,
        model="claude-opus-5-5",
        usage=SimpleNamespace(input_tokens=100, output_tokens=20),
    )


def _settings(**kw):
    return ExtractionSettings(_env_file=None, anthropic_api_key="k", **kw)


def test_anthropic_request_shape_and_parse():
    client = _Client(_msg(json.dumps(_PAYLOAD)))
    r = AnthropicExtractor(_settings(), client).extract(b"%PDF-1.4 hi", "a.pdf")
    kw = client.calls[0]
    doc = kw["messages"][0]["content"][0]
    assert doc["type"] == "document"
    assert doc["source"]["media_type"] == "application/pdf"
    assert base64.b64decode(doc["source"]["data"]) == b"%PDF-1.4 hi"
    assert kw["output_config"]["format"] == {"type": "json_schema", "schema": EXTRACTION_SCHEMA}
    assert kw["output_config"]["effort"] == "high"
    assert kw["thinking"] == {"type": "adaptive"}
    assert kw["fallbacks"] == "default"
    assert kw["model"] == "claude-opus-5-5"
    assert r.provider == "anthropic"
    assert r.fields["patient_first_name"].value == "Ann"
    assert r.fields["provider_name"].page == 2
    assert r.input_tokens == 100 and r.output_tokens == 20
    assert r.provider_candidates[0].role == "prescriber"


def test_schema_all_nullable_and_closed():
    assert EXTRACTION_SCHEMA["additionalProperties"] is False
    for k in FIELD_NAMES:
        props = EXTRACTION_SCHEMA["properties"][k]["properties"]
        assert all("null" in p["type"] for p in props.values())


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_bad_stop_reason_is_extraction_error(stop):
    client = _Client(_msg("{}", stop))
    with pytest.raises(ExtractionError):
        AnthropicExtractor(_settings(), client).extract(b"x", "a.pdf")


def test_timeout_is_extraction_error():
    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    client = _Client(exc=anthropic.APITimeoutError(request=req))
    with pytest.raises(ExtractionError):
        AnthropicExtractor(_settings(), client).extract(b"x", "a.pdf")


def test_malformed_json_is_extraction_error():
    client = _Client(_msg("not json"))
    with pytest.raises(ExtractionError):
        AnthropicExtractor(_settings(), client).extract(b"x", "a.pdf")


def test_missing_key_is_not_configured():
    with pytest.raises(ExtractionNotConfigured):
        AnthropicExtractor(ExtractionSettings(_env_file=None))


def test_api_error_is_extraction_error():
    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    exc = anthropic.APIConnectionError(request=req)
    client = _Client(exc=exc)
    with pytest.raises(ExtractionError):
        AnthropicExtractor(_settings(), client).extract(b"x", "a.pdf")


def test_no_text_block_is_extraction_error():
    client = _Client(_msg(None))
    with pytest.raises(ExtractionError):
        AnthropicExtractor(_settings(), client).extract(b"x", "a.pdf")


def test_client_built_with_no_retries_and_settings_timeout(monkeypatch):
    seen = {}

    class Spy:
        def __init__(self, **kw):
            seen.update(kw)

    monkeypatch.setattr(anthropic, "Anthropic", Spy)
    AnthropicExtractor(_settings())
    assert seen["max_retries"] == 0
    assert seen["timeout"] == 110
