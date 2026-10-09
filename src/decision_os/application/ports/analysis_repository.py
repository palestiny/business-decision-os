from typing import Protocol
from uuid import UUID

from decision_os.domain.analysis import AnalysisFinding


class AnalysisFindingRepository(Protocol):
    def get(self, finding_id: UUID, tenant_id: UUID) -> AnalysisFinding | None: ...
    def list_for_case(self, case_id: UUID, tenant_id: UUID) -> tuple[AnalysisFinding, ...]: ...
    def add(self, finding: AnalysisFinding, tenant_id: UUID) -> None: ...
