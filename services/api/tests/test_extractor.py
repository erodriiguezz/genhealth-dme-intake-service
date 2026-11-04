import pytest

from app.extraction import FIELD_NAMES, ExtractionNotConfigured, get_extractor
from app.extraction.fake import FakeExtractor
from app.extraction.settings import ExtractionSettings


def test_fake_extractor_returns_benchmark_shape():
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
