from time import perf_counter
from typing import Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "retentionops_api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "http_status"],
)

ERROR_COUNT = Counter(
    "retentionops_api_errors_total",
    "Total number of API errors",
    ["method", "endpoint"],
)

REQUEST_LATENCY = Histogram(
    "retentionops_api_latency_seconds",
    "API request latency in seconds",
    ["method", "endpoint"],
)

ACTION_COUNT = Counter(
    "retentionops_recommended_action_total",
    "Total number of recommended actions",
    ["action"],
)

UPLIFT_SCORE = Histogram(
    "retentionops_uplift_score",
    "Distribution of predicted uplift scores",
    buckets=(-1.0, -0.5, -0.2, -0.1, -0.05, 0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0),
)

EXPECTED_VALUE = Histogram(
    "retentionops_expected_incremental_value",
    "Distribution of expected incremental value",
    buckets=(-100.0, -50.0, -20.0, -10.0, -5.0, 0.0, 1.0, 5.0, 10.0, 20.0, 50.0, 100.0, 500.0),
)


def normalize_endpoint(path: str) -> str:
    if path == "/":
        return "/"

    return path.rstrip("/")


async def prometheus_middleware(request: Request, call_next: Callable) -> Response:
    endpoint = normalize_endpoint(request.url.path)

    if endpoint == "/metrics":
        return await call_next(request)

    method = request.method
    start_time = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        ERROR_COUNT.labels(method=method, endpoint=endpoint).inc()
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status="500").inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(
            perf_counter() - start_time
        )
        raise

    status_code = str(response.status_code)

    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        http_status=status_code,
    ).inc()

    if response.status_code >= 500:
        ERROR_COUNT.labels(method=method, endpoint=endpoint).inc()

    REQUEST_LATENCY.labels(
        method=method,
        endpoint=endpoint,
    ).observe(perf_counter() - start_time)

    return response


def record_decision_metrics(
    recommended_action: str,
    uplift_score: float,
    expected_incremental_value: float,
) -> None:
    ACTION_COUNT.labels(action=recommended_action).inc()
    UPLIFT_SCORE.observe(uplift_score)
    EXPECTED_VALUE.observe(expected_incremental_value)


def metrics_response() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
