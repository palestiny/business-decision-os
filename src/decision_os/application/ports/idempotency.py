"""Idempotency boundary for commands with side effects."""
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class IdempotencyConflict(ValueError):
    """Same key was reused with a different request."""


class RequestInProgress(RuntimeError):
    """A matching request is already executing."""


@dataclass(frozen=True)
class IdempotencyRecord:
    tenant_id: UUID
    operation: str
    key: str
    request_hash: str
    status: str
    response_status: int | None = None
    response_body: str | None = None


class IdempotencyPort(Protocol):
    def reserve(
        self,
        *,
        tenant_id: UUID,
        operation: str,
        key: str,
        request_hash: str,
    ) -> IdempotencyRecord:
        ...

    def complete(
        self,
        *,
        tenant_id: UUID,
        operation: str,
        key: str,
        response_status: int,
        response_body: str,
    ) -> None:
        ...
