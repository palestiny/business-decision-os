from datetime import datetime, timezone
from uuid import uuid4

import pytest

from decision_os.application.commands.create_evidence import CreateEvidenceCommand, CreateEvidenceHandler
from decision_os.application.commands.add_analysis_finding import AddAnalysisFindingCommand, AddAnalysisFindingHandler
from decision_os.domain.analysis import AnalysisKind, InvalidAnalysis
from decision_os.domain.decision_case import CaseStatus, DecisionCase


class Repo:
    def __init__(self):
        self.cases = {}
        self.evidence = []
        self.findings = []

    def get_case(self, case_id, tenant_id):
        return self.cases.get(case_id)

    def add_evidence(self, evidence, tenant_id):
        self.evidence.append(evidence)

    def list_evidence(self, case_id, tenant_id):
        return tuple(e for e in self.evidence if e.case_id == case_id)

    def add_finding(self, finding, tenant_id):
        self.findings.append(finding)

    def list_findings(self, case_id, tenant_id):
        return tuple(f for f in self.findings if f.case_id == case_id)


class Uow:
    def __init__(self):
        self.repo = Repo()
        self.decision_cases = self
        self.evidence = self.repo
        self.analysis_findings = self.repo

    def get(self, case_id, tenant_id):
        return self.repo.get_case(case_id, tenant_id)

    def commit(self): ...
    def rollback(self): ...


class AllowAuthorization:
    def require(self, **kwargs): ...


def seed_case(uow):
    tenant_id, actor_id, case_id = uuid4(), uuid4(), uuid4()
    uow.repo.cases[case_id] = DecisionCase(
        case_id, tenant_id, "PROJECT_MARGIN_RISK", "Margin risk", CaseStatus.ANALYZING, 2
    )
    return tenant_id, actor_id, case_id


def test_create_evidence_adds_immutable_business_fact():
    uow = Uow()
    tenant_id, actor_id, case_id = seed_case(uow)
    handler = CreateEvidenceHandler(uow, AllowAuthorization())
    evidence = handler.handle(CreateEvidenceCommand(
        tenant_id=tenant_id, case_id=case_id, actor_id=actor_id, evidence_id=uuid4(),
        source="PSA", metric="gross_margin_percent", value="12.5", unit="percent",
        period="2026-09", captured_at=datetime.now(timezone.utc), confidence=0.95,
        snapshot="project-123:margin",
    ))
    assert evidence.case_id == case_id
    assert uow.repo.evidence[0] == evidence


def test_add_analysis_finding_requires_referenced_evidence():
    uow = Uow()
    tenant_id, actor_id, case_id = seed_case(uow)
    handler = AddAnalysisFindingHandler(uow, AllowAuthorization())
    with pytest.raises(InvalidAnalysis):
        handler.handle(AddAnalysisFindingCommand(
            tenant_id=tenant_id, case_id=case_id, actor_id=actor_id, finding_id=uuid4(),
            kind=AnalysisKind.INFERENCE, statement="Costs are driving margin erosion.",
            confidence=0.8, evidence_ids=(uuid4(),),
        ))
