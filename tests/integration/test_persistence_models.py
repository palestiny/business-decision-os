from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from decision_os.infrastructure.persistence.base import Base
from decision_os.infrastructure.persistence import models  # noqa: F401


def test_metadata_contains_required_persistence_tables() -> None:
    expected = {
        "tenants", "decision_cases", "decision_options", "decisions",
        "decision_selected_options", "idempotency_records", "audit_events", "outbox_messages",
    }
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        assert expected.issubset(set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()


def test_decision_case_model_has_version_and_tenant_scope() -> None:
    from decision_os.infrastructure.persistence.models.decision_case import DecisionCaseModel

    assert DecisionCaseModel.__table__.c.version.nullable is False
    assert DecisionCaseModel.__table__.c.tenant_id.nullable is False


def test_idempotency_key_is_tenant_scoped_and_unique() -> None:
    from decision_os.infrastructure.persistence.models.reliability import IdempotencyRecordModel

    constraint_names = {c.name for c in IdempotencyRecordModel.__table__.constraints}
    assert "uq_idempotency_tenant_operation_key" in constraint_names
