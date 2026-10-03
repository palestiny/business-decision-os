"""Analysis findings with explicit epistemic classification."""
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class AnalysisKind(StrEnum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"


class InvalidAnalysis(ValueError):
    """Raised when an analysis finding violates a domain invariant."""


@dataclass(frozen=True)
class AnalysisFinding:
    id: UUID
    case_id: UUID
    kind: AnalysisKind
    statement: str
    confidence: float
    evidence_ids: tuple[UUID, ...]

    @classmethod
    def create(
        cls, *, id: UUID, case_id: UUID, kind: AnalysisKind, statement: str,
        confidence: float, evidence_ids: tuple[UUID, ...],
    ) -> "AnalysisFinding":
        if not statement.strip():
            raise InvalidAnalysis("analysis statement is required")
        if not 0 <= confidence <= 1:
            raise InvalidAnalysis("confidence must be between 0 and 1")
        if not evidence_ids:
            raise InvalidAnalysis("analysis finding requires evidence")
        if len(set(evidence_ids)) != len(evidence_ids):
            raise InvalidAnalysis("analysis evidence ids must be unique")
        return cls(
            id=id, case_id=case_id, kind=kind, statement=statement.strip(),
            confidence=confidence, evidence_ids=evidence_ids,
        )
