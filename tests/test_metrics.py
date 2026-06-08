from src.serving.metrics import normalize_endpoint


def test_normalize_endpoint_removes_trailing_slash():
    assert normalize_endpoint("/health/") == "/health"


def test_normalize_endpoint_keeps_root():
    assert normalize_endpoint("/") == "/"
