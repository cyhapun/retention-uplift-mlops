"use client";

import { FormEvent, useEffect, useState } from "react";

const features = Array.from({ length: 11 }, (_, index) => `f${index}`);
const operations = [
  ["train-uplift", "Train uplift model"],
  ["register-uplift", "Register champion"],
  ["drift-report", "Refresh drift report"],
  ["simulate-drift", "Simulate drift"],
  ["simulate-feedback", "Simulate feedback"],
] as const;

type Overview = {
  environment: string;
  refreshed_at: string;
  services: Array<{ name: string; status: string; detail?: string; latency_ms?: number }>;
  model: { model_name: string; model_alias: string; model_uri: string; model_loaded: boolean; mlflow_url: string };
  metrics: Record<string, number | Record<string, number> | null>;
  database: { decision_count: number; feedback_count: number; average_uplift?: number | null; observed_outcome_rate?: number; realized_value?: number; feedback_by_action?: Record<string, number>; recent_decisions?: Array<{ decision_id: string; user_id: string; recommended_action: string; uplift_score: number }>; error?: string };
  drift: { available: boolean; should_retrain?: boolean | null; n_drifted_features?: number | null; drifted_feature_share?: number | null; retrain_reasons?: string[]; report_url?: string };
  links: Record<string, string>;
};

type Decision = {
  decision_id: string;
  treatment_probability: number;
  control_probability: number;
  uplift_score: number;
  expected_incremental_value: number;
  roi: number;
  recommended_action: string;
  decision_reason: string[];
};

type Operation = { operation_id: string; operation: string; status: string; error_summary?: string };

function formatNumber(value: unknown, digits = 3) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

export default function Home() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [recentOperations, setRecentOperations] = useState<Operation[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [startingOperation, setStartingOperation] = useState("");
  const [operationMessage, setOperationMessage] = useState("");
  const [form, setForm] = useState({ user_id: "demo_user_001", customer_value: "100" });
  const [featureValues, setFeatureValues] = useState<Record<string, string>>(
    Object.fromEntries(features.map((feature) => [feature, "0"])),
  );

  const loadDashboard = async () => {
    try {
      const [overviewResponse, operationsResponse] = await Promise.all([
        fetch("/api/dashboard/overview", { cache: "no-store" }),
        fetch("/api/operations", { cache: "no-store" }),
      ]);
      if (!overviewResponse.ok) throw new Error("Dashboard service is unavailable.");
      setOverview(await overviewResponse.json());
      if (operationsResponse.ok) setRecentOperations(await operationsResponse.json());
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Dashboard failed to load.");
    }
  };

  useEffect(() => {
    loadDashboard();
    const interval = window.setInterval(loadDashboard, 15000);
    return () => window.clearInterval(interval);
  }, []);

  const submitDecision = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setDecision(null);
    try {
      const response = await fetch("/api/decisions", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          user_id: form.user_id,
          customer_value: Number(form.customer_value),
          features: Object.fromEntries(features.map((feature) => [feature, Number(featureValues[feature])])),
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail?.message ?? payload.detail ?? "Decision failed.");
      setDecision(payload);
      await loadDashboard();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Decision failed.");
    } finally {
      setBusy(false);
    }
  };

  const startOperation = async (operation: string) => {
    if (!window.confirm(`Start ${operation}?`)) return;
    setStartingOperation(operation);
    setOperationMessage("");
    try {
      const response = await fetch(`/api/operations/${operation}`, { method: "POST" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Operation could not be started.");
      setOperationMessage(`${operation} queued as ${payload.operation_id}.`);
      await loadDashboard();
    } catch (caught) {
      setOperationMessage(caught instanceof Error ? caught.message : "Operation failed.");
    } finally {
      setStartingOperation("");
    }
  };

  const healthyCount = overview?.services.filter((service) => service.status === "healthy").length ?? 0;
  const actionDistribution = overview?.metrics.action_distribution as Record<string, number> | undefined;

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">RETENTIONOPS / CONTROL CENTER</p>
          <h1>Operate the uplift platform from one place.</h1>
        </div>
        <div className="topbar-actions">
          <span className="pill">{overview?.environment ?? "loading"}</span>
          <button className="secondary" onClick={loadDashboard}>Refresh</button>
        </div>
      </header>

      {error && <div className="alert" role="alert">{error}</div>}

      <section className="hero-grid">
        <div className="hero-card accent"><p className="muted">Platform health</p><strong>{overview ? `${healthyCount}/${overview.services.length}` : "-"}</strong><span>services healthy</span></div>
        <div className="hero-card"><p className="muted">Champion model</p><strong>{overview?.model.model_loaded ? "Ready" : "Not ready"}</strong><span>{overview?.model.model_name ?? "uplift_model"}@{overview?.model.model_alias ?? "champion"}</span></div>
        <div className="hero-card"><p className="muted">Decisions logged</p><strong>{overview?.database.decision_count ?? "-"}</strong><span>{overview?.database.feedback_count ?? 0} feedback records</span></div>
        <div className="hero-card"><p className="muted">Drift signal</p><strong>{overview?.drift.available ? (overview.drift.should_retrain ? "Review" : "Normal") : "No report"}</strong><span>{overview?.drift.n_drifted_features ?? 0} drifted features</span></div>
      </section>

      <section className="content-grid">
        <div className="panel wide">
          <div className="panel-heading"><div><p className="eyebrow">LIVE SERVICES</p><h2>System health</h2></div><span className="muted">15s refresh</span></div>
          <div className="service-list">
            {overview?.services.map((service) => <div className="service-row" key={service.name}><span className={`status-dot ${service.status}`} /><strong>{service.name}</strong><span className="muted">{service.detail ?? service.status}</span><span className="metric-value">{service.latency_ms ? `${formatNumber(service.latency_ms, 0)} ms` : "-"}</span></div>) ?? <p className="muted">Loading service health...</p>}
          </div>
          <div className="link-row">
            {overview?.links.mlflow && <a href={overview.links.mlflow} target="_blank" rel="noreferrer">MLflow ↗</a>}
            {overview?.links.grafana && <a href={overview.links.grafana} target="_blank" rel="noreferrer">Grafana ↗</a>}
            {overview?.links.prometheus && <a href={overview.links.prometheus} target="_blank" rel="noreferrer">Prometheus ↗</a>}
            {overview?.links.api && <a href={`${overview.links.api}/docs`} target="_blank" rel="noreferrer">API docs ↗</a>}
          </div>
        </div>

        <div className="panel">
          <div className="panel-heading"><div><p className="eyebrow">DECISION PLAYGROUND</p><h2>Try a decision</h2></div></div>
          <form onSubmit={submitDecision} className="form-stack">
            <label>User ID<input required value={form.user_id} onChange={(event) => setForm({ ...form, user_id: event.target.value })} /></label>
            <label>Customer value<input required type="number" min="0.01" step="0.01" value={form.customer_value} onChange={(event) => setForm({ ...form, customer_value: event.target.value })} /></label>
            <div className="feature-grid">{features.map((feature) => <label key={feature}>{feature}<input required type="number" step="any" value={featureValues[feature]} onChange={(event) => setFeatureValues({ ...featureValues, [feature]: event.target.value })} /></label>)}</div>
            <button className="primary" disabled={busy || !overview?.model.model_loaded}>{busy ? "Scoring..." : "Run decision"}</button>
          </form>
          {decision && <div className="decision-result"><span className="eyebrow">RECOMMENDATION</span><strong>{decision.recommended_action}</strong><p>Decision ID: {decision.decision_id}</p><p>Uplift {formatNumber(decision.uplift_score)} · ROI {formatNumber(decision.roi)}</p><p>Treatment {formatNumber(decision.treatment_probability)} · Control {formatNumber(decision.control_probability)}</p><p>Expected value {formatNumber(decision.expected_incremental_value)}</p><p className="muted">{decision.decision_reason.join(" · ")}</p></div>}
        </div>

        <div className="panel">
          <div className="panel-heading"><div><p className="eyebrow">OPERATIONS</p><h2>Safe job controls</h2></div></div>
          <div className="operation-controls">{operations.map(([operation, label]) => <button className="secondary" key={operation} disabled={Boolean(startingOperation)} onClick={() => startOperation(operation)}>{startingOperation === operation ? "Starting..." : label}</button>)}</div>
          {operationMessage && <p className="small operation-message" role="status">{operationMessage}</p>}
          {recentOperations.length ? recentOperations.slice(0, 5).map((item) => <div className="job-row" key={item.operation_id}><strong>{item.operation}</strong><span className={`job-status ${item.status}`}>{item.status}</span></div>) : <p className="muted">No jobs recorded.</p>}
          <p className="small muted">Mutating operations require an admin token.</p>
        </div>

        <div className="panel wide">
          <div className="panel-heading"><div><p className="eyebrow">TELEMETRY</p><h2>Key metrics</h2></div></div>
          <div className="metric-grid"><div><span className="muted">Request rate</span><strong>{formatNumber(overview?.metrics.request_rate)} req/s</strong></div><div><span className="muted">Error rate</span><strong>{formatNumber(overview?.metrics.error_rate)} /s</strong></div><div><span className="muted">Average uplift</span><strong>{formatNumber(overview?.database.average_uplift ?? overview?.metrics.average_uplift)}</strong></div><div><span className="muted">Expected value</span><strong>{formatNumber(overview?.metrics.average_expected_value)}</strong></div></div>
          <p className="small muted metric-note">Actions: {actionDistribution ? Object.entries(actionDistribution).map(([action, count]) => `${action} ${formatNumber(count, 0)}`).join(" · ") : "No Prometheus data"}</p>
        </div>

        <div className="panel"><div className="panel-heading"><div><p className="eyebrow">DRIFT MONITORING</p><h2>Retraining signal</h2></div></div>{overview?.drift.available ? <><p>{overview.drift.n_drifted_features ?? 0} / 11 features drifted ({formatNumber((overview.drift.drifted_feature_share ?? 0) * 100, 1)}%).</p><p className="small muted">{overview.drift.retrain_reasons?.join(" · ") ?? "No retraining reasons."}</p>{overview.drift.report_url && <a href={overview.drift.report_url} target="_blank" rel="noreferrer">Open report summary ↗</a>}</> : <p className="muted">No drift report available.</p>}</div>

        <div className="panel"><div className="panel-heading"><div><p className="eyebrow">DECISION HISTORY</p><h2>Recent decisions</h2></div></div>{overview?.database.recent_decisions?.length ? overview.database.recent_decisions.map((item) => <div className="job-row" key={item.decision_id}><span><strong>{item.recommended_action}</strong><br /><span className="small muted">{item.user_id}</span></span><span className="metric-value">{formatNumber(item.uplift_score)}</span></div>) : <p className="muted">No decisions recorded.</p>}<p className="small muted">Feedback records: {overview?.database.feedback_count ?? 0}; observed outcome rate: {formatNumber(overview?.database.observed_outcome_rate)}</p></div>
      </section>
      <footer>RetentionOps Control Center · refreshed {overview ? new Date(overview.refreshed_at).toLocaleTimeString() : "-"}</footer>
    </main>
  );
}
