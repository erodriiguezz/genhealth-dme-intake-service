from .base import ExtractionNotConfigured, Extractor
from .settings import ExtractionSettings, get_extraction_settings


def get_extractor(settings: ExtractionSettings | None = None) -> Extractor:
    s = settings or get_extraction_settings()
    if s.extraction_provider == "fake":
        if s.env.lower() == "production":
            raise ExtractionNotConfigured("fake extraction provider is refused in production")
        from .fake import FakeExtractor

        return FakeExtractor()
    from .anthropic_extractor import AnthropicExtractor

    return AnthropicExtractor(s)
