import os
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, close_all_sessions

from decision_os.application.commands.approve_decision import (
    ApproveDecisionCommand,
    ApproveDecisionHandler,
)
from decision_os.application.ports.authority import (
    Permission,
    SeparationOfDutiesViolation,
)
from decision_os.domain.decision import Decision, DecisionOption, DecisionStatus
from decision_os.domain.decision_case import CaseStatus, DecisionCase
from decision_os.infrastructure.persistence.models.decision import DecisionOptionModel
from decision_os.infrastructure.persistence.models.tenant import TenantModel
from decision_os.infrastructure.persistence.repositories.decision import SQLAlchemyDecisionRepository
from decision_os.infrastructure.persistence.repositories.decision_case import SQLAlchemyDecisionCaseRepository
from decision_os.infrastructure.persistence.session import build_session_factory
from decision_os.infrastructure.persistence.uow import SQLAlchemyUnitOfWork


DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="SQLALCHEMY_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture()
def session():
    factory = build_session_factory(DATABASE_URL)
    with factory() as db:
        yield db
        db.rollback()
    close_all_sessions()


class AllowApproveAuthorization:
    def __init__(self):
        self.calls = []

    def require(self, **kwargs):
        self.calls.append(kwargs)
        assert kwargs["permission"] is Permission.APPROVE_DECISION


def seed_pending_decision(session: Session, *, creator_id, decision_maker_id):
    tenant_id = uuid4()
    session.add(TenantModel(id=tenant_id, name=f"four-eyes-{tenant_id}"))
    session.commit()

    case = DecisionCase.create(
        id=uuid4(),
        tenant_id=tenant_id,
        case_type="PROJECT_MARGIN_RISK",
        title="Four-eyes integration case",
        created_by=creator_id,
    )
    case.status = CaseStatus.AWAITING_APPROVAL
    case.version = 2
    case_repository = SQLAlchemyDecisionCaseRepository(session)
    case_repository.add(case)
    session.flush()

    option = DecisionOption(id=uuid4(), case_id=case.id, title="Protect margin")
    session.add(DecisionOptionModel(id=option.id, case_id=option.case_id, title=option.title))
    decision = Decision.make(
        id=uuid4(),
        case_id=case.id,
        available_options=(option,),
        selected_option_ids=(option.id,),
        rationale="Protect delivery margin.",
        decided_by=decision_maker_id,
        approval_required=True,
    )
    SQLAlchemyDecisionRepository(session).add(decision)
    session.commit()
    return tenant_id, case, decision


@pytest.mark.parametrize("same_as", ["creator", "decision_maker"])
def test_postgres_denies_creator_or_decision_maker_as_approver(session: Session, same_as: str):
    creator_id, decision_maker_id = uuid4(), uuid4()
    approver_id = creator_id if same_as == "creator" else decision_maker_id
    tenant_id, case, decision = seed_pending_decision(
        session, creator_id=creator_id, decision_maker_id=decision_maker_id
    )
    authorization = AllowApproveAuthorization()
    handler = ApproveDecisionHandler(SQLAlchemyUnitOfWork(session), authorization)

    with pytest.raises(SeparationOfDutiesViolation):
        handler.handle(ApproveDecisionCommand(
            tenant_id=tenant_id,
            case_id=case.id,
            decision_id=decision.id,
            actor_id=approver_id,
        ))

    assert authorization.calls[0]["actor_id"] == approver_id
    session.expire_all()
    persisted_case = SQLAlchemyDecisionCaseRepository(session).get(case.id, tenant_id)
    persisted_decision = SQLAlchemyDecisionRepository(session).get(decision.id, tenant_id)
    assert persisted_case is not None
    assert persisted_case.status is CaseStatus.AWAITING_APPROVAL
    assert persisted_decision is not None
    assert persisted_decision.status is DecisionStatus.AWAITING_APPROVAL
    assert persisted_decision.approved_by is None
    assert persisted_decision.approved_at is None


def test_postgres_fails_closed_when_legacy_case_has_no_creator_attribution(session: Session):
    tenant_id, case, decision = seed_pending_decision(
        session, creator_id=None, decision_maker_id=uuid4()
    )
    authorization = AllowApproveAuthorization()
    handler = ApproveDecisionHandler(SQLAlchemyUnitOfWork(session), authorization)

    with pytest.raises(SeparationOfDutiesViolation, match="creator attribution"):
        handler.handle(ApproveDecisionCommand(
            tenant_id=tenant_id,
            case_id=case.id,
            decision_id=decision.id,
            actor_id=uuid4(),
        ))

    session.expire_all()
    persisted_case = SQLAlchemyDecisionCaseRepository(session).get(case.id, tenant_id)
    persisted_decision = SQLAlchemyDecisionRepository(session).get(decision.id, tenant_id)
    assert persisted_case is not None
    assert persisted_case.status is CaseStatus.AWAITING_APPROVAL
    assert persisted_decision is not None
    assert persisted_decision.status is DecisionStatus.AWAITING_APPROVAL
    assert persisted_decision.approved_by is None
    assert persisted_decision.approved_at is None
