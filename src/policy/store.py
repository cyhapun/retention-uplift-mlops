import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select

from src.db.database import SessionLocal
from src.db.models import DecisionLog, PolicyAudit, PolicyVersion
from src.demo_config import demo_local_history_enabled
from src.policy.config import ActionConfig, PolicyConfig, load_policy_config
from src.policy.schemas import PolicyDocument


class PolicyConflictError(RuntimeError):
    """Raised when a policy was changed since a form was opened."""


def policy_store_enabled() -> bool:
    configured = os.getenv("POLICY_STORE_ENABLED")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    return os.getenv("DATABASE_URL", "").startswith("postgresql")


def policy_config_to_dict(config: PolicyConfig) -> dict:
    return {
        "actions": {
            name: {
                "cost": action.cost,
                "min_expected_value": action.min_expected_value,
                "min_uplift": action.min_uplift,
                "priority": action.priority,
            }
            for name, action in config.actions.items()
        },
        "min_uplift_for_action": config.min_uplift_for_action,
        "max_daily_budget": config.max_daily_budget,
    }


def policy_document_to_config(document: PolicyDocument) -> PolicyConfig:
    validate_policy_document(document)
    return PolicyConfig(
        actions={
            name: ActionConfig(
                name=name,
                cost=values.cost,
                min_expected_value=values.min_expected_value,
                min_uplift=values.min_uplift,
                priority=values.priority,
            )
            for name, values in document.actions.items()
        },
        min_uplift_for_action=document.min_uplift_for_action,
        max_daily_budget=document.max_daily_budget,
    )


def policy_config_to_document(config: PolicyConfig) -> PolicyDocument:
    return PolicyDocument(
        actions={
            name: {
                "cost": action.cost,
                "min_expected_value": action.min_expected_value,
                "min_uplift": action.min_uplift,
                "priority": action.priority,
            }
            for name, action in config.actions.items()
        },
        min_uplift_for_action=config.min_uplift_for_action,
        max_daily_budget=config.max_daily_budget,
    )


def validate_policy_document(document: PolicyDocument) -> None:
    errors: list[str] = []
    if "no_action" not in document.actions:
        errors.append("The policy must include a no-action rule.")
    if len(document.actions) < 2:
        errors.append("The policy must include at least one offer besides no action.")
    priorities = [
        action.priority for name, action in document.actions.items() if name != "no_action"
    ]
    if len(priorities) != len(set(priorities)):
        errors.append("Offer priorities must be unique.")
    no_action = document.actions.get("no_action")
    if no_action and no_action.cost != 0:
        errors.append("The no-action rule must have zero cost.")
    if any(name.strip() == "" for name in document.actions):
        errors.append("Action names must not be empty.")
    if errors:
        raise ValueError(" ".join(errors))


def ensure_policy_seed() -> None:
    if not policy_store_enabled():
        return
    with SessionLocal() as session:
        active = session.scalar(select(PolicyVersion).where(PolicyVersion.is_active.is_(True)))
        if active is not None:
            return
        config = load_policy_config()
        version = PolicyVersion(
            version_id=str(uuid4()),
            version_number=1,
            config=policy_config_to_dict(config),
            created_by="system-seed",
            activated_at=datetime.now(timezone.utc),
            is_active=True,
            change_summary="Initial policy seeded from YAML configuration.",
        )
        session.add(version)
        if not demo_local_history_enabled():
            session.add(
                PolicyAudit(
                    audit_id=str(uuid4()),
                    action="seed",
                    actor="system-seed",
                    status="accepted",
                    outcome="Initial policy activated.",
                    target_version_id=version.version_id,
                )
            )
        session.commit()


def get_active_policy() -> tuple[PolicyConfig, PolicyVersion | None]:
    if not policy_store_enabled():
        return load_policy_config(), None
    ensure_policy_seed()
    with SessionLocal() as session:
        version = session.scalar(select(PolicyVersion).where(PolicyVersion.is_active.is_(True)))
        if version is None:
            return load_policy_config(), None
        return policy_document_to_config(PolicyDocument.model_validate(version.config)), version


def get_policy_snapshot() -> tuple[PolicyDocument, PolicyVersion | None]:
    config, version = get_active_policy()
    return policy_config_to_document(config), version


def activate_policy(
    document: PolicyDocument,
    actor: str,
    expected_version_id: str | None,
    confirm: bool,
    change_summary: str,
    action: str = "activate",
    source_version_id: str | None = None,
) -> PolicyVersion:
    validate_policy_document(document)
    if not confirm:
        raise ValueError("Explicit confirmation is required before activating a policy.")
    if not policy_store_enabled():
        raise RuntimeError("Policy persistence is not configured.")

    with SessionLocal() as session:
        active = session.scalar(
            select(PolicyVersion).where(PolicyVersion.is_active.is_(True)).with_for_update()
        )
        actual_id = active.version_id if active else None
        if expected_version_id is not None and expected_version_id != actual_id:
            raise PolicyConflictError("The active policy changed. Reload it before saving.")

        highest_version = session.scalar(select(func.max(PolicyVersion.version_number))) or 0
        if active:
            active.is_active = False
        version = PolicyVersion(
            version_id=str(uuid4()),
            version_number=int(highest_version) + 1,
            config=document.model_dump(mode="json"),
            created_by=actor,
            activated_at=datetime.now(timezone.utc),
            is_active=True,
            parent_version_id=actual_id,
            change_summary=change_summary or "Policy updated.",
        )
        session.add(version)
        if not demo_local_history_enabled():
            session.add(
                PolicyAudit(
                    audit_id=str(uuid4()),
                    action=action,
                    actor=actor,
                    status="accepted",
                    outcome=change_summary or "Policy activated.",
                    source_version_id=source_version_id or actual_id,
                    target_version_id=version.version_id,
                )
            )
        session.commit()
        session.refresh(version)
        return version


def rollback_policy(
    version_id: str,
    actor: str,
    expected_version_id: str | None,
    confirm: bool,
) -> PolicyVersion:
    if not policy_store_enabled():
        raise RuntimeError("Policy persistence is not configured.")
    with SessionLocal() as session:
        target = session.get(PolicyVersion, version_id)
        if target is None:
            raise LookupError("Policy version not found.")
        document = PolicyDocument.model_validate(target.config)
    return activate_policy(
        document=document,
        actor=actor,
        expected_version_id=expected_version_id,
        confirm=confirm,
        change_summary=f"Rolled back to policy version {target.version_number}.",
        action="rollback",
        source_version_id=version_id,
    )


def list_policy_versions(limit: int = 25) -> list[PolicyVersion]:
    if not policy_store_enabled():
        return []
    with SessionLocal() as session:
        statement = select(PolicyVersion).order_by(PolicyVersion.version_number.desc()).limit(limit)
        return list(session.scalars(statement).all())


def list_policy_audits(limit: int = 50) -> list[PolicyAudit]:
    if not policy_store_enabled() or demo_local_history_enabled():
        return []
    with SessionLocal() as session:
        statement = select(PolicyAudit).order_by(PolicyAudit.created_at.desc()).limit(limit)
        return list(session.scalars(statement).all())


def record_policy_rejection(
    action: str,
    actor: str,
    outcome: str,
    source_version_id: str | None = None,
) -> None:
    if not policy_store_enabled() or demo_local_history_enabled():
        return
    with SessionLocal() as session:
        session.add(
            PolicyAudit(
                audit_id=str(uuid4()),
                action=action,
                actor=actor,
                status="rejected",
                outcome=outcome[:1000],
                source_version_id=source_version_id,
            )
        )
        session.commit()


def preview_policy(document: PolicyDocument, limit: int = 1000) -> dict:
    config = policy_document_to_config(document)
    with SessionLocal() as session:
        statement = select(DecisionLog).order_by(DecisionLog.created_at.desc()).limit(limit)
        decisions = list(session.scalars(statement).all())
    if not decisions:
        return {
            "available": False,
            "reason": "There are no logged decisions to use for an estimate.",
        }

    from src.policy.decision_engine import recommend_action_from_policy

    distribution: dict[str, int] = {}
    changed = 0
    values: list[float] = []
    periods = [item.created_at for item in decisions if item.created_at is not None]
    for item in decisions:
        result = recommend_action_from_policy(item.uplift_score, item.customer_value, config)
        action_name = str(result["recommended_action"])
        distribution[action_name] = distribution.get(action_name, 0) + 1
        values.append(float(result["expected_incremental_value"]))
        if action_name != item.recommended_action:
            changed += 1
    period = None
    if periods:
        period = f"{min(periods).isoformat()} to {max(periods).isoformat()}"
    return {
        "available": True,
        "population": len(decisions),
        "evaluation_period": period,
        "changed_decisions": changed,
        "estimated_action_distribution": distribution,
        "estimated_average_expected_value": sum(values) / len(values),
    }
