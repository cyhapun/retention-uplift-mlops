export const ACTION_LABELS: Record<string, string> = {
  no_action: "No retention offer",
  low_cost_email: "Low-cost email",
  standard_discount: "Standard discount",
  premium_offer: "Premium offer",
};

export const REASON_LABELS: Record<string, string> = {
  positive_uplift: "The offer is expected to improve retention.",
  positive_expected_value: "The expected value is higher than the treatment cost.",
  action_threshold_met: "The recommendation meets the configured policy threshold.",
  non_positive_uplift: "The offer is not expected to improve retention.",
  below_global_uplift_threshold: "The uplift is below the minimum level for an offer.",
  no_action_met_policy_thresholds: "No available offer meets the current policy thresholds.",
};

export const OPERATION_LABELS: Record<string, string> = {
  "train-uplift": "Train the uplift model",
  "register-uplift": "Register the champion model",
  "drift-report": "Refresh the drift report",
  "simulate-drift": "Simulate data drift",
  "simulate-feedback": "Simulate delayed feedback",
};

export const SERVICE_LABELS: Record<string, string> = {
  api: "Decision API",
  mlflow: "MLflow model registry",
  prometheus: "Prometheus metrics",
  grafana: "Grafana dashboards",
  postgres: "PostgreSQL database",
  ops: "Operations control",
};

export const METRIC_LABELS: Record<string, { label: string; unit: string; description: string }> = {
  request_rate: { label: "Decision requests", unit: "requests / second", description: "How many decisions the API is handling." },
  error_rate: { label: "API errors", unit: "errors / second", description: "Requests that ended with an error." },
  average_uplift: { label: "Average uplift", unit: "score", description: "Average estimated incremental effect of an offer." },
  average_expected_value: { label: "Average expected value", unit: "value units", description: "Average value after treatment cost." },
  average_latency_seconds: { label: "Response time", unit: "seconds", description: "Average API response time." },
};

export const FEATURE_LABELS: Record<string, { label: string; description: string }> = Object.fromEntries(
  Array.from({ length: 11 }, (_, index) => [
    `f${index}`,
    { label: `Customer attribute ${index + 1}`, description: "Advanced model input; confirm its meaning in the data dictionary." },
  ]),
);

export function actionLabel(value: string) {
  return ACTION_LABELS[value] ?? value.replaceAll("_", " ");
}

export function reasonLabel(value: string) {
  return REASON_LABELS[value] ?? value.replaceAll("_", " ");
}

export function operationLabel(value: string) {
  return OPERATION_LABELS[value] ?? value.replaceAll("-", " ");
}

export function serviceLabel(value: string) {
  return SERVICE_LABELS[value] ?? value;
}

export function formatNumber(value: unknown, digits = 3) {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function formatPercent(value: unknown, digits = 1) {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatTime(value?: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Not available" : date.toLocaleString();
}

export function safeError(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string") return message;
    }
  }
  return fallback;
}
