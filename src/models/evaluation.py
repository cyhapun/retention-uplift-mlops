import math
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score


def get_positive_class_proba(model: Any, x_valid) -> np.ndarray:
    if not hasattr(model, "predict_proba"):
        raise AttributeError("Model must implement predict_proba().")

    proba = model.predict_proba(x_valid)

    if proba.ndim != 2 or proba.shape[1] < 2:
        raise ValueError("predict_proba() must return an array with at least 2 columns.")

    return proba[:, 1]


def safe_roc_auc(y_true, y_score) -> float:
    try:
        return float(roc_auc_score(y_true, y_score))
    except ValueError:
        return math.nan


def safe_average_precision(y_true, y_score) -> float:
    try:
        return float(average_precision_score(y_true, y_score))
    except ValueError:
        return math.nan


def safe_log_loss(y_true, y_score) -> float:
    try:
        return float(log_loss(y_true, y_score, labels=[0, 1]))
    except ValueError:
        return math.nan


def evaluate_binary_classifier(model: Any, x_valid, y_valid) -> dict[str, float]:
    y_score = get_positive_class_proba(model, x_valid)

    return {
        "roc_auc": safe_roc_auc(y_valid, y_score),
        "pr_auc": safe_average_precision(y_valid, y_score),
        "log_loss": safe_log_loss(y_valid, y_score),
    }