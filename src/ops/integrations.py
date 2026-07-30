import json
import os
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select, text

from src.db.database import SessionLocal
from src.db.feedback_repository import get_feedback_summary_by_action
from src.db.models import DecisionLog, FeedbackLog
from src.db.repository import get_action_distribution, get_average_uplift_score
from src.ops.schemas import DashboardOverview, DriftSummary, ModelSummary, ServiceStatus
from src.runtime_paths import DRIFT_REPORT_ROOT

REQUEST_TIMEOUT = float(os.getenv("OPS_UPSTREAM_TIMEOUT_SECONDS", "3"))
DRIFT_SUMMARY_PATH = DRIFT_REPORT_ROOT / "data_drift_report_summary.json"


def _public_url(name: str, default: str) -> str:
    return os.getenv(f"{name}_PUBLIC_URL", default)


PUBLIC_LINKS = {
    "dashboard": os.getenv("WEB_PUBLIC_URL", "http://localhost:3000"),
    "api": _public_url("API", "http://localhost:8000"),
    "mlflow": _public_url("MLFLOW", "http://localhost:5000"),
    "prometheus": _public_url("PROMETHEUS", "http://localhost:9090"),
    "grafana": _public_url("GRAFANA", "http://localhost:3001"),
}


def _get(url: str, path: str = "") -> tuple[bool, dict | str, float]:
    started = time.perf_counter()
    try:
        response = httpx.get(
            f"{url.rstrip('/')}/{path.lstrip('/')}",
            timeout=REQUEST_TIMEOUT,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        try:
            return True, response.json(), elapsed_ms
        except json.JSONDecodeError:
            return True, response.text, elapsed_ms
    except (httpx.HTTPError, ValueError) as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return False, str(exc), elapsed_ms


def get_service_health() -> list[ServiceStatus]:
    checks = [
        ("api", os.getenv("API_INTERNAL_URL", "http://api:8000"), "health"),
        ("mlflow", os.getenv("MLFLOW_INTERNAL_URL", "http://mlflow:5000"), "health"),
        (
            "prometheus",
            os.getenv("PROMETHEUS_INTERNAL_URL", "http://prometheus:9090"),
            "-/healthy",
        ),
        (
            "grafana",
            os.getenv("GRAFANA_INTERNAL_URL", "http://grafana:3000"),
            "api/health",
        ),
    ]
    services = []

    for name, url, path in checks:
        ok, payload, latency_ms = _get(url, path)
        services.append(
            ServiceStatus(
                name=name,
                status="healthy" if ok else "unavailable",
                detail=None if ok else str(payload),
                latency_ms=round(latency_ms, 2),
            )
        )

    started = time.perf_counter()
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        services.append(
            ServiceStatus(
                name="postgres",
                status="healthy",
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        )
    except Exception as exc:  # pragma: no cover - depends on external database
        services.append(
            ServiceStatus(
                name="postgres",
                status="unavailable",
                detail=str(exc),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        )

    services.append(ServiceStatus(name="ops", status="healthy"))
    return services


def get_model_summary() -> ModelSummary:
    api_url = os.getenv("API_INTERNAL_URL", "http://api:8000")
    ok, payload, _ = _get(api_url, "model-info")
    if not ok or not isinstance(payload, dict):
        return ModelSummary(
            model_name=os.getenv("UPLIFT_MODEL_NAME", "uplift_model"),
            model_alias=os.getenv("UPLIFT_MODEL_ALIAS", "champion"),
            model_uri="unknown",
            model_loaded=False,
            mlflow_url=PUBLIC_LINKS["mlflow"],
        )

    return ModelSummary(
        model_name=str(payload.get("model_name", "uplift_model")),
        model_alias=str(payload.get("model_alias", "champion")),
        model_uri=str(payload.get("model_uri", "unknown")),
        model_loaded=bool(payload.get("model_loaded", False)),
        mlflow_url=PUBLIC_LINKS["mlflow"],
    )


def _prometheus_query(expression: str) -> list[dict]:
    base_url = os.getenv("PROMETHEUS_INTERNAL_URL", "http://prometheus:9090")
    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/api/v1/query",
            params={"query": expression},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            return []
        return payload.get("data", {}).get("result", [])
    except (httpx.HTTPError, ValueError):
        return []


def _result_value(result: list[dict]) -> float | None:
    if not result:
        return None
    try:
        return float(result[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def get_metrics() -> dict:
    expressions = {
        "request_rate": "sum(rate(retentionops_api_requests_total[5m]))",
        "error_rate": "sum(rate(retentionops_api_errors_total[5m]))",
        "average_uplift": (
            "sum(rate(retentionops_uplift_score_sum[5m])) "
            "/ sum(rate(retentionops_uplift_score_count[5m]))"
        ),
        "average_expected_value": (
            "sum(rate(retentionops_expected_incremental_value_sum[5m])) "
            "/ sum(rate(retentionops_expected_incremental_value_count[5m]))"
        ),
        "average_latency_seconds": (
            "sum(rate(retentionops_api_latency_seconds_sum[5m])) "
            "/ sum(rate(retentionops_api_latency_seconds_count[5m]))"
        ),
    }
    metrics = {
        name: _result_value(_prometheus_query(expression))
        for name, expression in expressions.items()
    }

    action_results = _prometheus_query("sum(retentionops_recommended_action_total) by (action)")
    metrics["action_distribution"] = {
        item.get("metric", {}).get("action", "unknown"): _result_value([item]) or 0.0
        for item in action_results
    }
    return metrics


def get_database_summary() -> dict:
    try:
        with SessionLocal() as session:
            decision_count = session.scalar(select(func.count(DecisionLog.decision_id))) or 0
            feedback_count = session.scalar(select(func.count(FeedbackLog.feedback_id))) or 0
            observed_outcome_rate = session.scalar(func.avg(FeedbackLog.observed_outcome))
            realized_value = session.scalar(func.sum(FeedbackLog.realized_value)) or 0.0
            recent_decisions = session.scalars(
                select(DecisionLog).order_by(DecisionLog.created_at.desc()).limit(5)
            ).all()
            return {
                "decision_count": int(decision_count),
                "feedback_count": int(feedback_count),
                "average_uplift": get_average_uplift_score(session),
                "action_distribution": get_action_distribution(session),
                "feedback_by_action": get_feedback_summary_by_action(session),
                "observed_outcome_rate": float(observed_outcome_rate or 0.0),
                "realized_value": float(realized_value),
                "recent_decisions": [
                    {
                        "decision_id": item.decision_id,
                        "user_id": item.user_id,
                        "recommended_action": item.recommended_action,
                        "uplift_score": item.uplift_score,
                        "created_at": item.created_at,
                    }
                    for item in recent_decisions
                ],
            }
    except Exception as exc:  # pragma: no cover - depends on external database
        return {"error": str(exc), "decision_count": 0, "feedback_count": 0}


def get_drift_summary() -> DriftSummary:
    if not DRIFT_SUMMARY_PATH.exists():
        return DriftSummary(available=False)

    try:
        payload = json.loads(DRIFT_SUMMARY_PATH.read_text(encoding="utf-8"))
        return DriftSummary(
            available=True,
            report_name=payload.get("report_name"),
            dataset_drift_detected=payload.get("dataset_drift_detected"),
            n_features=payload.get("n_features"),
            n_drifted_features=payload.get("n_drifted_features"),
            drifted_feature_share=payload.get("drifted_feature_share"),
            drifted_features=payload.get("drifted_features", []),
            should_retrain=payload.get("should_retrain"),
            retrain_reasons=payload.get("retrain_reasons", []),
            report_url=f"{PUBLIC_LINKS['dashboard']}/api/dashboard/drift",
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return DriftSummary(available=False)


def get_overview() -> DashboardOverview:
    return DashboardOverview(
        environment=os.getenv("APP_ENV", "local"),
        refreshed_at=datetime.now(timezone.utc),
        services=get_service_health(),
        model=get_model_summary(),
        metrics=get_metrics(),
        database=get_database_summary(),
        drift=get_drift_summary(),
        links=PUBLIC_LINKS,
    )
