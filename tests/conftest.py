"""Keep the unit suite deterministic regardless of the developer's Compose env file."""

import pytest


@pytest.fixture(autouse=True)
def durable_default_for_tests(monkeypatch):
    monkeypatch.setenv("DEMO_LOCAL_HISTORY", "false")
