"""Offline CLI for explicitly authorized tenant access provisioning."""
import argparse
import json
import os
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from decision_os.infrastructure.persistence.provisioning import SQLAlchemyAuthorizationProvisioner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="decision-os-admin")
    parser.add_argument("--database-url", default=os.getenv("SQLALCHEMY_DATABASE_URL"))
    sub = parser.add_subparsers(dest="command", required=True)
    provision = sub.add_parser("provision", help="plan or provision one external identity grant")
    provision.add_argument("--issuer", required=True)
    provision.add_argument("--subject", required=True)
    provision.add_argument("--tenant-key", required=True)
    provision.add_argument("--tenant-id", required=True, type=UUID)
    provision.add_argument("--role", required=True)
    provision.add_argument("--actor-id", type=UUID, help="explicitly link an existing actor")
    provision.add_argument("--operator", default=os.getenv("DECISION_OS_ADMIN_OPERATOR"))
    provision.add_argument("--confirm", action="store_true", help="commit the planned changes")
    revoke = sub.add_parser("revoke-membership", help="revoke a tenant membership")
    revoke.add_argument("--membership-id", required=True, type=UUID)
    revoke.add_argument("--operator", default=os.getenv("DECISION_OS_ADMIN_OPERATOR"))
    revoke.add_argument("--confirm", action="store_true", help="commit the revocation")
    revoke_role = sub.add_parser("revoke-role", help="revoke one role assignment")
    revoke_role.add_argument("--assignment-id", required=True, type=UUID)
    revoke_role.add_argument("--operator", default=os.getenv("DECISION_OS_ADMIN_OPERATOR"))
    revoke_role.add_argument("--confirm", action="store_true", help="commit the revocation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or SQLALCHEMY_DATABASE_URL is required")
    if not args.operator or not args.operator.strip():
        raise SystemExit("--operator or DECISION_OS_ADMIN_OPERATOR is required")
    engine = create_engine(args.database_url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    try:
        service = SQLAlchemyAuthorizationProvisioner(factory)
        if args.command == "provision":
            plan = service.plan_provision(
                issuer=args.issuer, subject=args.subject, tenant_key=args.tenant_key,
                tenant_id=args.tenant_id, role_key=args.role, actor_id=args.actor_id,
            )
            if not args.confirm:
                print(json.dumps({"mode": "dry-run", "plan": plan.as_dict()}, sort_keys=True))
                return 0
            result = service.apply_provision(plan=plan, operator=args.operator)
            print(json.dumps({"mode": "committed", "result": result}, sort_keys=True))
            return 0
        if not args.confirm:
            print(json.dumps({
                "mode": "dry-run", "operation": args.command,
                "target_id": str(args.membership_id if args.command == "revoke-membership" else args.assignment_id),
                "operator": args.operator,
            }, sort_keys=True))
            return 0
        if args.command == "revoke-membership":
            result = service.revoke_membership(membership_id=args.membership_id, operator=args.operator)
        else:
            result = service.revoke_assignment(assignment_id=args.assignment_id, operator=args.operator)
        print(json.dumps({"mode": "committed", "result": result}, sort_keys=True))
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
