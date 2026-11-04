from .base import ExtractionResult, FieldResult, ProviderCandidate
from .prompt import PROMPT_VERSION


class FakeExtractor:
    """Deterministic extractor returning the CPAP benchmark values."""

    def extract(self, pdf_bytes: bytes, filename: str) -> ExtractionResult:
        return ExtractionResult(
            provider="fake",
            model="fake",
            prompt_version=PROMPT_VERSION,
            latency_ms=1,
            input_tokens=0,
            output_tokens=0,
            fields={
                "patient_first_name": FieldResult(value="Marie", evidence="Marie Curie", page=1),
                "patient_last_name": FieldResult(value="Curie", evidence="Marie Curie", page=1),
                "patient_dob": FieldResult(
                    value="12/05/1900", evidence="Patient Date of Birth 12/05/1900", page=1
                ),
                "provider_name": FieldResult(
                    value="Arjun Raj D.P.M",
                    evidence="Prescriber Name and Address Arjun Raj D.P.M",
                    page=1,
                ),
                "provider_npi": FieldResult(
                    value="9182734556", evidence="Prescriber NPI: 9182734556", page=1
                ),
            },
            provider_candidates=[
                ProviderCandidate(
                    name="Arjun Raj D.P.M", role="prescriber", npi="9182734556", page=1
                ),
                ProviderCandidate(name="Gregory House MD", role="referring physician", page=2),
            ],
        )
