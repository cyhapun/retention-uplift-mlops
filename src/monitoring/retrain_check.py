from dataclasses import dataclass


@dataclass(frozen=True)
class RetrainDecision:
    should_retrain: bool
    reasons: list[str]


def should_retrain(
    drift_detected: bool,
    drifted_feature_share: float,
    max_allowed_drifted_feature_share: float = 0.3,
    critical_features_drifted: list[str] | None = None,
) -> RetrainDecision:
    reasons = []

    if critical_features_drifted is None:
        critical_features_drifted = []

    if drift_detected:
        reasons.append("dataset_drift_detected")

    if drifted_feature_share > max_allowed_drifted_feature_share:
        reasons.append("drifted_feature_share_above_threshold")

    if critical_features_drifted:
        reasons.append("critical_features_drifted")

    return RetrainDecision(
        should_retrain=bool(reasons),
        reasons=reasons,
    )
