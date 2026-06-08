from src.monitoring.retrain_check import should_retrain


def test_should_retrain_when_dataset_drift_detected():
    decision = should_retrain(
        drift_detected=True,
        drifted_feature_share=0.1,
    )

    assert decision.should_retrain is True
    assert "dataset_drift_detected" in decision.reasons


def test_should_retrain_when_drifted_feature_share_above_threshold():
    decision = should_retrain(
        drift_detected=False,
        drifted_feature_share=0.5,
        max_allowed_drifted_feature_share=0.3,
    )

    assert decision.should_retrain is True
    assert "drifted_feature_share_above_threshold" in decision.reasons


def test_should_not_retrain_when_no_drift_signal():
    decision = should_retrain(
        drift_detected=False,
        drifted_feature_share=0.1,
        max_allowed_drifted_feature_share=0.3,
    )

    assert decision.should_retrain is False
    assert decision.reasons == []