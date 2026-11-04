from dataclasses import asdict, dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class Issue:
    field: str
    code: str
    severity: Literal["error", "warning"]
    message: str
    source: Literal["validation", "extraction"] = "validation"

    def to_json(self) -> dict[str, Any]:
        return asdict(self)
