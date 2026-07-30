"""Runtime-owned paths that must stay outside the source tree."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_default_report_root = Path(tempfile.gettempdir()) / "retentionops" / "reports"
REPORT_ROOT = Path(os.getenv("RETENTIONOPS_REPORT_ROOT", str(_default_report_root)))
DRIFT_REPORT_ROOT = REPORT_ROOT / "drift"
UPLIFT_REPORT_ROOT = REPORT_ROOT / "uplift"
