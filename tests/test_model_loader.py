from src.serving.model_loader import get_model_uri


def test_get_model_uri_default(monkeypatch):
    monkeypatch.delenv("UPLIFT_MODEL_NAME", raising=False)
    monkeypatch.delenv("UPLIFT_MODEL_ALIAS", raising=False)

    assert get_model_uri() == "models:/uplift_model@champion"


def test_get_model_uri_from_env(monkeypatch):
    monkeypatch.setenv("UPLIFT_MODEL_NAME", "test_model")
    monkeypatch.setenv("UPLIFT_MODEL_ALIAS", "staging")

    assert get_model_uri() == "models:/test_model@staging"