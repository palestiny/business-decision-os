from typing import Protocol
from uuid import UUID

from decision_os.domain.evidence import Evidence


class EvidenceRepository(Protocol):
    def get(self, evidence_id: UUID, tenant_id: UUID) -> Evidence | None: ...
    def list_for_case(self, case_id: UUID, tenant_id: UUID) -> tuple[Evidence, ...]: ...
    def add(self, evidence: Evidence, tenant_id: UUID) -> None: ...
