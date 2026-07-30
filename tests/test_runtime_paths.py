from pathlib import Path

from src.db.database import DEFAULT_DATABASE_URL
from src.runtime_paths import REPORT_ROOT


def test_local_defaults_do_not_create_project_runtime_artifacts():
    project_root = Path(__file__).resolve().parents[1]

    assert DEFAULT_DATABASE_URL == "sqlite:///:memory:"
    assert project_root not in REPORT_ROOT.parents
    assert REPORT_ROOT != project_root / "reports"
