"""Business outcome and verification domain primitives."""
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class OutcomeStatus(StrEnum):
    PENDING = "PENDING"
    OBSERVED = "OBSERVED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"


class InvalidOutcome(ValueError):
    """Raised when an outcome violates a domain invariant."""


@dataclass
class ExpectedOutcome:
    id: UUID
    case_id: UUID
    metric: str
    operator: str
    target: float

    @classmethod
    def create(cls, *, id: UUID, case_id: UUID, metric: str, operator: str, target: float) -> "ExpectedOutcome":
        if not metric.strip():
            raise InvalidOutcome("metric is required")
        if operator not in {"GT", "GTE", "EQ", "LTE", "LT"}:
            raise InvalidOutcome("unsupported verification operator")
        return cls(id=id, case_id=case_id, metric=metric.strip(), operator=operator, target=target)


@dataclass
class ActualOutcome:
    id: UUID
    case_id: UUID
    expected_outcome_id: UUID
    observed_value: float
    status: OutcomeStatus = OutcomeStatus.OBSERVED

    def mark_unknown(self) -> None:
        self.status = OutcomeStatus.UNKNOWN

    def mark_verified(self) -> None:
        self.status = OutcomeStatus.VERIFIED

    def mark_failed(self) -> None:
        self.status = OutcomeStatus.FAILED


@dataclass
class Verification:
    id: UUID
    case_id: UUID
    actual_outcome_id: UUID
    status: VerificationStatus = VerificationStatus.PENDING

    def verify(self, *, expected: ExpectedOutcome, actual: ActualOutcome) -> VerificationStatus:
        if actual.status is OutcomeStatus.UNKNOWN:
            self.status = VerificationStatus.INCONCLUSIVE
            return self.status
        if expected.id != actual.expected_outcome_id:
            raise InvalidOutcome("outcome does not match expected outcome")
        checks = {
            "GT": actual.observed_value > expected.target,
            "GTE": actual.observed_value >= expected.target,
            "EQ": actual.observed_value == expected.target,
            "LTE": actual.observed_value <= expected.target,
            "LT": actual.observed_value < expected.target,
        }
        self.status = VerificationStatus.PASSED if checks[expected.operator] else VerificationStatus.FAILED
        return self.status
