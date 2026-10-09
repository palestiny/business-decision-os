import json
from uuid import uuid4

from decision_os.admin.provisioning_cli import main


def test_cli_requires_explicit_confirm_for_mutations(monkeypatch, capsys):
    tenant_id = uuid4()
    calls = []

    class FakeProvisioner:
        def __init__(self, factory):
            pass
        def plan_provision(self, **kwargs):
            calls.append(("plan", kwargs))
            class Plan:
                def as_dict(self):
                    return {"tenant_id": str(tenant_id), "role_key": "read_only_reviewer"}
            return Plan()
        def apply_provision(self, **kwargs):
            calls.append(("apply", kwargs))
            return {"ok": True}

    import decision_os.admin.provisioning_cli as cli
    monkeypatch.setattr(cli, "SQLAlchemyAuthorizationProvisioner", FakeProvisioner)
    monkeypatch.setattr(cli, "create_engine", lambda *a, **kw: type("Engine", (), {"dispose": lambda self: None})())
    monkeypatch.setattr(cli, "sessionmaker", lambda **kw: object())
    assert main([
        "--database-url", "postgresql://unused", "provision",
        "--issuer", "https://issuer.example", "--subject", "subject",
        "--tenant-key", "tenant", "--tenant-id", str(tenant_id),
        "--role", "read_only_reviewer", "--operator", "ops",
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "dry-run"
    assert [c[0] for c in calls] == ["plan"]
