from subprocess import CompletedProcess

import pytest
from fastapi.testclient import TestClient

import src.ops.integrations as integrations
import src.ops.main as ops_main
from src.db.models import OperationRun
from src.ops.main import _require_admin
from src.ops.runner import ALLOWED_OPERATIONS, OperationRunner
from src.ops.schemas import ModelSummary


def test_operations_are_allowlisted():
    assert set(ALLOWED_OPERATIONS) == {
        "train-uplift",
        "register-uplift",
        "drift-report",
        "simulate-drift",
        "simulate-feedback",
    }
    assert all(command[0:2] == ["python", "-m"] for command in ALLOWED_OPERATIONS.values())


def test_admin_operations_are_disabled_without_token(monkeypatch):
    monkeypatch.delenv("OPS_ADMIN_TOKEN", raising=False)

    with pytest.raises(Exception) as error:
        _require_admin(None)

    assert getattr(error.value, "status_code", None) == 503


def test_admin_operations_require_matching_bearer_token(monkeypatch):
    monkeypatch.setenv("OPS_ADMIN_TOKEN", "test-token")

    with pytest.raises(Exception) as error:
        _require_admin("Bearer wrong-token")

    assert getattr(error.value, "status_code", None) == 401
    assert _require_admin("Bearer test-token") == "admin"


def test_ops_health_endpoint_is_available():
    client = TestClient(ops_main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mutating_endpoint_rejects_unconfigured_authentication(monkeypatch):
    monkeypatch.delenv("OPS_ADMIN_TOKEN", raising=False)

    with TestClient(ops_main.app) as client:
        response = client.post("/operations/drift-report")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_model_summary_handles_unavailable_api(monkeypatch):
    monkeypatch.setattr(integrations, "_get", lambda *_args, **_kwargs: (False, "timeout", 3.0))

    summary = integrations.get_model_summary()

    assert isinstance(summary, ModelSummary)
    assert summary.model_loaded is False
    assert summary.model_alias == "champion"


def test_drift_summary_handles_malformed_report(monkeypatch, tmp_path):
    report_path = tmp_path / "malformed.json"
    report_path.write_text('{"n_drifted_features": {"bad": true}}', encoding="utf-8")
    monkeypatch.setattr(integrations, "DRIFT_SUMMARY_PATH", report_path)

    summary = integrations.get_drift_summary()

    assert summary.available is False


def test_stale_jobs_are_reconciled_without_claiming_success(monkeypatch):
    stale_job = OperationRun(
        operation_id="stale-job",
        operation="train-uplift",
        actor="admin",
        status="running",
        command_summary="python -m src.models.train_uplift_model",
    )

    class FakeResult:
        def all(self):
            return [stale_job]

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def scalars(self, _query):
            return FakeResult()

        def commit(self):
            return None

    monkeypatch.setattr("src.ops.runner.SessionLocal", lambda: FakeSession())

    runner = OperationRunner()
    try:
        assert runner.reconcile_stale_jobs() == 1
        assert stale_job.status == "failed"
        assert "restarted" in stale_job.error_summary
    finally:
        runner.shutdown()


def test_duplicate_operation_is_rejected(monkeypatch):
    running_job = OperationRun(
        operation_id="running-job",
        operation="train-uplift",
        actor="admin",
        status="running",
        command_summary="python -m src.models.train_uplift_model",
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def scalar(self, _query):
            return running_job

    monkeypatch.setattr("src.ops.runner.SessionLocal", lambda: FakeSession())
    runner = OperationRunner()
    try:
        with pytest.raises(RuntimeError, match="running-job"):
            runner.start("drift-report", "admin")
    finally:
        runner.shutdown()


def test_runner_records_successful_subprocess_transition(monkeypatch):
    finished = {}
    runner = OperationRunner()
    monkeypatch.setattr(
        "src.ops.runner.subprocess.run",
        lambda *_args, **_kwargs: CompletedProcess(
            args=["python", "-m", "demo"],
            returncode=0,
            stdout="completed",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        runner,
        "_finish",
        lambda **kwargs: finished.update(kwargs),
    )
    monkeypatch.setattr(
        "src.ops.runner.SessionLocal",
        lambda: type(
            "SessionContext",
            (),
            {
                "__enter__": lambda self: self,
                "__exit__": lambda self, *_args: False,
                "get": lambda self, _model, _operation_id: OperationRun(
                    operation_id="job",
                    operation="drift-report",
                    actor="admin",
                    status="queued",
                    command_summary="python -m demo",
                ),
                "commit": lambda self: None,
            },
        )(),
    )

    try:
        runner._run("job", ["python", "-m", "demo"])
        assert finished["status"] == "succeeded"
        assert finished["output_tail"] == "completed"
    finally:
        runner.shutdown()


def test_demo_local_runner_does_not_open_a_database_session(monkeypatch):
    monkeypatch.setattr(
        "src.ops.runner.SessionLocal",
        lambda: (_ for _ in ()).throw(AssertionError("demo-local jobs must not use PostgreSQL")),
    )
    monkeypatch.setattr(
        "src.ops.runner.subprocess.run",
        lambda *_args, **_kwargs: CompletedProcess(
            args=["python", "-m", "demo"], returncode=0, stdout="completed", stderr=""
        ),
    )
    runner = OperationRunner(demo_local=True)
    try:
        operation = runner.start("drift-report", "admin")
        runner.executor.shutdown(wait=True)
        assert operation.status == "succeeded"
        assert runner.list()[0].operation_id == operation.operation_id
    finally:
        runner.shutdown()


def test_demo_local_runner_moves_feedback_simulation_to_browser(monkeypatch):
    runner = OperationRunner(demo_local=True)
    try:
        with pytest.raises(ValueError, match="simulated in the browser"):
            runner.start("simulate-feedback", "admin")
    finally:
        runner.shutdown()
