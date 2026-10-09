"""Request-scoped composition for the create-case command boundary."""
from typing import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from decision_os.application.commands.create_decision_case import CreateDecisionCaseCommand, CreateDecisionCaseHandler
from decision_os.application.commands.triage_case import TriageCaseCommand, TriageCaseHandler
from decision_os.application.commands.start_analysis import StartAnalysisCommand, StartAnalysisHandler
from decision_os.application.commands.create_evidence import CreateEvidenceCommand, CreateEvidenceHandler
from decision_os.application.commands.add_analysis_finding import AddAnalysisFindingCommand, AddAnalysisFindingHandler
from decision_os.application.ports.authority import AuthorizationPort
from decision_os.application.reliability import CreateDecisionCaseReliabilityBoundary
from decision_os.application.triage_reliability import TriageCaseReliabilityBoundary
from decision_os.application.start_analysis_reliability import StartAnalysisReliabilityBoundary
from decision_os.application.create_evidence_reliability import CreateEvidenceReliabilityBoundary
from decision_os.application.add_analysis_finding_reliability import AddAnalysisFindingReliabilityBoundary
from decision_os.infrastructure.persistence.repositories.reliability import (
    SQLAlchemyAuditRepository,
    SQLAlchemyIdempotencyRepository,
    SQLAlchemyOutboxRepository,
)
from decision_os.infrastructure.persistence.uow import SQLAlchemyUnitOfWork


class SessionScopedCreateDecisionCaseBoundary:
    """Compose all create-case persistence adapters over one short-lived Session.

    The Session is opened for one command execution and closed even if validation,
    persistence, audit/outbox writes, or transaction commit fails.
    """

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        authorization: AuthorizationPort,
    ) -> None:
        self._session_factory = session_factory
        self._authorization = authorization

    def execute(
        self,
        command: CreateDecisionCaseCommand,
        *,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ):
        with self._session_factory() as session:
            uow = SQLAlchemyUnitOfWork(session)
            boundary = CreateDecisionCaseReliabilityBoundary(
                uow=uow,
                handler=CreateDecisionCaseHandler(uow, self._authorization),
                idempotency=SQLAlchemyIdempotencyRepository(session),
                audit=SQLAlchemyAuditRepository(session),
                outbox=SQLAlchemyOutboxRepository(session),
            )
            return boundary.execute(
                command,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )



class SessionScopedTriageCaseBoundary:
    """Compose triage command adapters over one short-lived Session/transaction."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        authorization: AuthorizationPort,
    ) -> None:
        self._session_factory = session_factory
        self._authorization = authorization

    def execute(
        self,
        command: TriageCaseCommand,
        *,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ):
        with self._session_factory() as session:
            uow = SQLAlchemyUnitOfWork(session)
            boundary = TriageCaseReliabilityBoundary(
                uow=uow,
                handler=TriageCaseHandler(uow, self._authorization),
                idempotency=SQLAlchemyIdempotencyRepository(session),
                audit=SQLAlchemyAuditRepository(session),
                outbox=SQLAlchemyOutboxRepository(session),
            )
            return boundary.execute(
                command,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )



class SessionScopedStartAnalysisBoundary:
    """Compose start-analysis command adapters over one short-lived Session/transaction."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        authorization: AuthorizationPort,
    ) -> None:
        self._session_factory = session_factory
        self._authorization = authorization

    def execute(
        self,
        command: StartAnalysisCommand,
        *,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ):
        with self._session_factory() as session:
            uow = SQLAlchemyUnitOfWork(session)
            boundary = StartAnalysisReliabilityBoundary(
                uow=uow,
                handler=StartAnalysisHandler(uow, self._authorization),
                idempotency=SQLAlchemyIdempotencyRepository(session),
                audit=SQLAlchemyAuditRepository(session),
                outbox=SQLAlchemyOutboxRepository(session),
            )
            return boundary.execute(
                command,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )



class SessionScopedCreateEvidenceBoundary:
    """Compose create-evidence command adapters over one short-lived Session/transaction."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        authorization: AuthorizationPort,
    ) -> None:
        self._session_factory = session_factory
        self._authorization = authorization

    def execute(
        self,
        command: CreateEvidenceCommand,
        *,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ):
        with self._session_factory() as session:
            uow = SQLAlchemyUnitOfWork(session)
            boundary = CreateEvidenceReliabilityBoundary(
                uow=uow,
                handler=CreateEvidenceHandler(uow, self._authorization),
                idempotency=SQLAlchemyIdempotencyRepository(session),
                audit=SQLAlchemyAuditRepository(session),
                outbox=SQLAlchemyOutboxRepository(session),
            )
            return boundary.execute(
                command,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )



class SessionScopedAddAnalysisFindingBoundary:
    """Compose add-analysis-finding adapters over one short-lived Session/transaction."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        authorization: AuthorizationPort,
    ) -> None:
        self._session_factory = session_factory
        self._authorization = authorization

    def execute(
        self,
        command: AddAnalysisFindingCommand,
        *,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ):
        with self._session_factory() as session:
            uow = SQLAlchemyUnitOfWork(session)
            boundary = AddAnalysisFindingReliabilityBoundary(
                uow=uow,
                handler=AddAnalysisFindingHandler(uow, self._authorization),
                idempotency=SQLAlchemyIdempotencyRepository(session),
                audit=SQLAlchemyAuditRepository(session),
                outbox=SQLAlchemyOutboxRepository(session),
            )
            return boundary.execute(
                command,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
