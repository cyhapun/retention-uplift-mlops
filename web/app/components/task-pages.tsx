"use client";

import { useCallback, useEffect, useState } from "react";

import { ControlCenterShell, LoadingState, MetricCard, PageIntro, Panel, PanelHeading, StatusMessage, TechnicalDetails } from "./control-center-shell";
import { DecisionForm } from "./decision-form";
import { actionLabel, formatNumber, formatPercent, formatTime, METRIC_LABELS, operationLabel, reasonLabel, safeError, serviceLabel } from "./presentation";

export type Overview = {
  environment: string;
  refreshed_at: string;
  services: Array<{ name: string; status: string; detail?: string; latency_ms?: number }>;
  model: { model_name: string; model_alias: string; model_uri: string; model_loaded: boolean; mlflow_url: string };
  metrics: Record<string, number | Record<string, number> | null>;
  database: { decision_count: number; feedback_count: number; average_uplift?: number | null; observed_outcome_rate?: number; realized_value?: number; feedback_by_action?: Record<string, number>; recent_decisions?: Array<{ decision_id: string; user_id: string; recommended_action: string; uplift_score: number; created_at?: string }> ; error?: string };
  drift: { available: boolean; should_retrain?: boolean | null; n_features?: number | null; n_drifted_features?: number | null; drifted_feature_share?: number | null; drifted_features?: string[]; retrain_reasons?: string[]; report_url?: string };
  links: Record<string, string>;
};

type Operation = { operation_id: string; operation: string; actor: string; status: string; created_at?: string; finished_at?: string; error_summary?: string; command_summary?: string };

function useOverview() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const response = await fetch("/api/dashboard/overview", { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(safeError(payload, "The platform overview is unavailable."));
      setOverview(payload);
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The platform overview is unavailable.");
    } finally {
      setRefreshing(false);
    }
  }, []);
  useEffect(() => { load(); const interval = window.setInterval(load, 15000); return () => window.clearInterval(interval); }, [load]);
  return { overview, error, refreshing, load };
}

function GlobalError({ error, retry }: { error: string; retry: () => void }) {
  return error ? <StatusMessage kind="error"><div className="inline-feedback"><span>{error}</span><button className="text-button" onClick={retry}>Try again</button></div></StatusMessage> : null;
}

function SpecialistLinks({ links, include = ["mlflow", "grafana", "prometheus", "api"] }: { links: Record<string, string>; include?: string[] }) {
  return <div className="link-row">{include.filter((name) => links[name]).map((name) => <a href={name === "api" ? `${links[name]}/docs` : links[name]} target="_blank" rel="noreferrer" key={name}>{name === "api" ? "API documentation" : name === "mlflow" ? "Explore models in MLflow" : name === "grafana" ? "Open Grafana dashboards" : "Inspect Prometheus metrics"} ↗</a>)}</div>;
}

function ShellPage({ active, intro, children, onRefresh, overview, refreshing }: { active: string; intro: { eyebrow: string; title: string; description: string }; children: React.ReactNode; onRefresh?: () => void; overview?: Overview | null; refreshing?: boolean }) {
  return <ControlCenterShell active={active} environment={overview?.environment} refreshedAt={overview?.refreshed_at} onRefresh={onRefresh} refreshing={refreshing}><PageIntro {...intro} />{children}</ControlCenterShell>;
}

export function OverviewPage() {
  const { overview, error, refreshing, load } = useOverview();
  if (!overview && refreshing) return <ControlCenterShell active="/" onRefresh={load} refreshing><LoadingState /></ControlCenterShell>;
  const healthyCount = overview?.services.filter((service) => service.status === "healthy").length ?? 0;
  const actionDistribution = overview?.metrics.action_distribution as Record<string, number> | undefined;
  return <ShellPage active="/" intro={{ eyebrow: "PLATFORM OVERVIEW", title: "Operate the uplift platform with confidence.", description: "See what is healthy, what needs attention, and where to go next." }} onRefresh={load} overview={overview} refreshing={refreshing}>
    <GlobalError error={error} retry={load} />
    <div className="hero-grid"><MetricCard label="Platform health" value={overview ? `${healthyCount}/${overview.services.length}` : "—"} unit="services healthy" description="Availability across the Control Center stack." /><MetricCard label="Champion model" value={overview?.model.model_loaded ? "Ready" : "Not ready"} unit={overview ? `${overview.model.model_name}@${overview.model.model_alias}` : "Waiting for model status"} description="The model used for live decisions." /><MetricCard label="Decisions logged" value={String(overview?.database.decision_count ?? "—")} unit={`${overview?.database.feedback_count ?? 0} feedback records`} description="Decisions currently stored for review." /><MetricCard label="Drift signal" value={overview?.drift.available ? (overview.drift.should_retrain ? "Review needed" : "Normal") : "No report"} unit={`${overview?.drift.n_drifted_features ?? 0} features changed`} description="Whether recent input data differs from the reference." /></div>
    <div className="content-grid overview-grid">
      <Panel className="wide"><PanelHeading eyebrow="LIVE SERVICES" title="System health" action={<span className="muted small">Checks every 15 seconds</span>} /><div className="service-list">{overview?.services.map((service) => <div className="service-row" key={service.name}><span className={`status-dot ${service.status}`} /><strong>{serviceLabel(service.name)}</strong><span className="muted service-detail">{service.status === "healthy" ? "Available" : "Needs attention"}</span><span className="metric-value">{service.latency_ms ? `${formatNumber(service.latency_ms, 0)} ms` : "—"}</span>{service.detail && <TechnicalDetails title="Details"><p>{service.detail}</p></TechnicalDetails>}</div>) ?? <LoadingState label="Checking services…" />}</div><SpecialistLinks links={overview?.links ?? {}} /></Panel>
      <Panel><PanelHeading eyebrow="MODEL STATUS" title="Champion model" /><div className={`model-status ${overview?.model.model_loaded ? "ready" : "warning"}`}><span className="status-dot healthy" /><strong>{overview?.model.model_loaded ? "Ready for decisions" : "Not ready yet"}</strong></div><p className="panel-description">{overview?.model.model_loaded ? "The current champion model is available to score customer profiles." : "Load a champion model before running a decision."}</p>{overview?.model.model_loaded && <TechnicalDetails><p>Model name: {overview.model.model_name}</p><p>Alias: {overview.model.model_alias}</p><p>Run reference: <code>{overview.model.model_uri}</code></p></TechnicalDetails>}</Panel>
      <Panel><PanelHeading eyebrow="RECENT DECISIONS" title="What happened recently" />{overview?.database.recent_decisions?.length ? overview.database.recent_decisions.map((item) => <div className="job-row" key={item.decision_id}><span><strong>{actionLabel(item.recommended_action)}</strong><small className="muted">{item.user_id}</small></span><span className="metric-value">{formatNumber(item.uplift_score)}</span></div>) : <p className="muted">No decisions have been logged yet.</p>}</Panel>
      <Panel className="wide"><PanelHeading eyebrow="KEY METRICS" title="Platform signals" /><div className="metric-grid">{["request_rate", "error_rate", "average_uplift", "average_expected_value"].map((key) => { const meta = METRIC_LABELS[key]; return <MetricCard key={key} label={meta.label} value={formatNumber(overview?.metrics[key])} unit={meta.unit} description={meta.description} />; })}</div><p className="small muted metric-note">{actionDistribution ? `Actions recorded: ${Object.entries(actionDistribution).map(([action, count]) => `${actionLabel(action)} (${formatNumber(count, 0)})`).join(" · ")}` : "Action distribution is not available yet."}</p></Panel>
    </div>
  </ShellPage>;
}

export function DecisionsPage() {
  const { overview, error, refreshing, load } = useOverview();
  return <ShellPage active="/decisions" intro={{ eyebrow: "DECISIONS", title: "Make a decision you can explain.", description: "Test a customer profile and understand the recommendation, value estimate, and reason behind it." }} onRefresh={load} overview={overview} refreshing={refreshing}><GlobalError error={error} retry={load} /><div className="content-grid two-column"><DecisionForm modelReady={Boolean(overview?.model.model_loaded)} onCompleted={load} /><Panel><PanelHeading eyebrow="HOW TO READ THIS" title="A practical guide" /><div className="guide-list"><div><strong>Uplift</strong><p className="muted">The estimated difference in retention caused by offering treatment instead of doing nothing.</p></div><div><strong>Expected value</strong><p className="muted">Estimated uplift multiplied by customer value, minus the offer cost.</p></div><div><strong>Estimated customer value</strong><p className="muted">A business assumption used for this calculation. The model does not discover it automatically.</p></div><div><strong>Recommendation</strong><p className="muted">The highest-priority action that passes the active policy thresholds.</p></div></div><SpecialistLinks links={overview?.links ?? {}} include={["mlflow", "api"]} /></Panel></div></ShellPage>;
}

export function MonitoringPage() {
  const { overview, error, refreshing, load } = useOverview();
  const drift = overview?.drift;
  return <ShellPage active="/monitoring" intro={{ eyebrow: "MONITORING", title: "Know when the platform needs attention.", description: "Monitor service availability, decision traffic, and whether incoming customer data still resembles the training reference." }} onRefresh={load} overview={overview} refreshing={refreshing}><GlobalError error={error} retry={load} /><div className="metric-grid monitoring-metrics">{["request_rate", "error_rate", "average_latency_seconds", "average_uplift", "average_expected_value"].map((key) => { const meta = METRIC_LABELS[key] ?? { label: key, unit: "value", description: "Platform signal." }; return <MetricCard key={key} label={meta.label} value={formatNumber(overview?.metrics[key])} unit={meta.unit} description={meta.description} />; })}</div><div className="content-grid two-column"><Panel><PanelHeading eyebrow="DRIFT MONITORING" title="Input-data change" />{drift?.available ? <><div className={`signal-banner ${drift.should_retrain ? "warning" : "success"}`}><strong>{drift.should_retrain ? "Review recommended" : "No action recommended"}</strong><span>{drift.n_drifted_features ?? 0} of {drift.n_features ?? 11} tracked attributes changed materially.</span></div><p className="panel-description">Drift means that recent customer data has a different distribution from the reference data used to assess the model. It is a signal to investigate, not an automatic retraining command.</p>{drift.retrain_reasons?.length ? <div className="reason-list"><span className="muted">Why it was flagged</span>{drift.retrain_reasons.map((reason) => <span key={reason}>• {reasonLabel(reason)}</span>)}</div> : null}{drift.report_url && <a href={drift.report_url} target="_blank" rel="noreferrer">Open the detailed drift summary ↗</a>}</> : <StatusMessage kind="info">No drift report is available yet. Run “Refresh the drift report” from Operations.</StatusMessage>}</Panel><Panel><PanelHeading eyebrow="SERVICE HEALTH" title="Where the platform stands" />{overview?.services.map((service) => <div className="service-row" key={service.name}><span className={`status-dot ${service.status}`} /><strong>{serviceLabel(service.name)}</strong><span className="muted service-detail">{service.status === "healthy" ? "Available" : "Needs attention"}</span></div>)}<SpecialistLinks links={overview?.links ?? {}} include={["grafana", "prometheus"]} /></Panel></div></ShellPage>;
}

export function OperationsPage() {
  const { overview, error, refreshing, load } = useOverview();
  const [operations, setOperations] = useState<Operation[]>([]);
  const [starting, setStarting] = useState("");
  const [message, setMessage] = useState("");
  const loadOperations = useCallback(async () => { const response = await fetch("/api/operations", { cache: "no-store" }); if (response.ok) setOperations(await response.json()); }, []);
  useEffect(() => { loadOperations(); }, [loadOperations]);
  const startOperation = async (operation: string) => { if (!window.confirm(`Start “${operationLabel(operation)}”?`)) return; setStarting(operation); setMessage(""); try { const response = await fetch(`/api/operations/${operation}`, { method: "POST" }); const payload = await response.json(); if (!response.ok) throw new Error(safeError(payload, "The operation could not be started.")); setMessage(`${operationLabel(operation)} is queued.`); await Promise.all([loadOperations(), load()]); } catch (caught) { setMessage(caught instanceof Error ? caught.message : "The operation could not be started."); } finally { setStarting(""); } };
  const operationList = [["train-uplift", "Retrain uplift model", "Build a new model from the prepared training data."], ["register-uplift", "Register champion model", "Make a validated model available to the API."], ["drift-report", "Refresh drift report", "Compare recent data with the reference dataset."], ["simulate-drift", "Simulate data drift", "Create a controlled data-change scenario for a demo."], ["simulate-feedback", "Simulate delayed feedback", "Generate feedback records for recent decisions."]] as const;
  return <ShellPage active="/operations" intro={{ eyebrow: "OPERATIONS", title: "Run safe platform jobs.", description: "Start approved MLOps workflows with a clear status and a concise result. The control plane never exposes arbitrary shell commands." }} onRefresh={() => { load(); loadOperations(); }} overview={overview} refreshing={refreshing}><GlobalError error={error} retry={load} /><div className="content-grid two-column"><Panel><PanelHeading eyebrow="SAFE JOB CONTROLS" title="Approved workflows" />{!message ? null : <StatusMessage kind={message.includes("queued") ? "success" : "error"}>{message}</StatusMessage>}<div className="operation-cards">{operationList.map(([operation, label, description]) => <div className="operation-card" key={operation}><div><strong>{label}</strong><p className="muted">{description}</p></div><button className="secondary" disabled={Boolean(starting)} onClick={() => startOperation(operation)}>{starting === operation ? "Starting…" : "Start job"}</button></div>)}</div><p className="small muted">Changing platform state requires an administrator token configured on the server.</p></Panel><Panel><PanelHeading eyebrow="JOB HISTORY" title="Recent workflow runs" />{operations.length ? operations.slice(0, 8).map((item) => <div className="job-row" key={item.operation_id}><span><strong>{operationLabel(item.operation)}</strong><small className="muted">{formatTime(item.created_at)}</small></span><span className={`job-status ${item.status}`}>{item.status === "succeeded" ? "Completed" : item.status === "failed" ? "Failed" : item.status}</span>{item.error_summary && <TechnicalDetails><p>{item.error_summary}</p></TechnicalDetails>}</div>) : <p className="muted">No jobs have been recorded yet.</p>}</Panel></div></ShellPage>;
}
