"""Immutable business evidence domain primitive."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class InvalidEvidence(ValueError):
    """Raised when evidence violates a domain invariant."""


@dataclass(frozen=True)
class Evidence:
    id: UUID
    case_id: UUID
    source: str
    metric: str
    value: str
    unit: str
    period: str
    captured_at: datetime
    confidence: float
    snapshot: str

    @classmethod
    def create(
        cls, *, id: UUID, case_id: UUID, source: str, metric: str, value: str,
        unit: str, period: str, captured_at: datetime, confidence: float, snapshot: str,
    ) -> "Evidence":
        if not source.strip():
            raise InvalidEvidence("source is required")
        if not metric.strip():
            raise InvalidEvidence("metric is required")
        if not value.strip():
            raise InvalidEvidence("value is required")
        if not period.strip():
            raise InvalidEvidence("period is required")
        if not snapshot.strip():
            raise InvalidEvidence("snapshot is required")
        if not 0 <= confidence <= 1:
            raise InvalidEvidence("confidence must be between 0 and 1")
        return cls(
            id=id, case_id=case_id, source=source.strip(), metric=metric.strip(),
            value=value.strip(), unit=unit.strip(), period=period.strip(),
            captured_at=captured_at, confidence=confidence, snapshot=snapshot.strip(),
        )
