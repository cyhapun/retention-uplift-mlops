import numpy as np

from src.models.evaluation import evaluate_binary_classifier, get_positive_class_proba


class DummyBinaryModel:
    def predict_proba(self, x):
        return np.array(
            [
                [0.9, 0.1],
                [0.2, 0.8],
                [0.7, 0.3],
                [0.1, 0.9],
            ]
        )


def test_get_positive_class_proba_returns_second_column():
    model = DummyBinaryModel()
    x = np.zeros((4, 2))

    proba = get_positive_class_proba(model, x)

    assert proba.tolist() == [0.1, 0.8, 0.3, 0.9]


def test_evaluate_binary_classifier_returns_expected_metrics():
    model = DummyBinaryModel()
    x = np.zeros((4, 2))
    y = np.array([0, 1, 0, 1])

    metrics = evaluate_binary_classifier(model, x, y)

    assert set(metrics.keys()) == {"roc_auc", "pr_auc", "log_loss"}
    assert metrics["roc_auc"] == 1.0
    assert metrics["pr_auc"] == 1.0
    assert metrics["log_loss"] > 0