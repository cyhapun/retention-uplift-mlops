from src.serving.model_loader import build_model_uri


def test_build_model_uri_uses_name_and_alias():
    uri = build_model_uri(
        model_name="uplift_model",
        model_alias="champion",
    )

    assert uri == "models:/uplift_model@champion"