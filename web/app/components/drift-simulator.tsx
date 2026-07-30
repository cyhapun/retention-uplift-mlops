"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Panel, PanelHeading, StatusMessage } from "./control-center-shell";
import { formatNumber, formatTime, safeError } from "./presentation";

type Preset = "low" | "medium" | "high" | "advanced";
type TransformOperation = "scale_percent" | "shift";
type Transformation = { feature: string; operation: TransformOperation; value: number };

type FeatureSummary = {
  feature: string;
  operation: TransformOperation;
  value: number;
  before_mean: number;
  after_mean: number;
  before_std: number;
  after_std: number;
};

export type DriftSimulation = {
  simulation_id: string;
  status: string;
  preset?: string | null;
  rows: number;
  transformations: Transformation[];
  summary?: {
    rows: number;
    affected_feature_count: number;
    severity: "low" | "medium" | "high";
    affected_features: FeatureSummary[];
  } | null;
  created_at?: string;
  finished_at?: string;
  expires_at?: string;
  error_summary?: string | null;
  downloads?: Array<{ format: "parquet" | "csv"; url: string }>;
};

const FEATURES = Array.from({ length: 11 }, (_, index) => `f${index}`);
const DEFAULT_ADVANCED: Record<string, Transformation> = Object.fromEntries(
  FEATURES.map((feature) => [feature, { feature, operation: "scale_percent", value: 10 }]),
);

function featureLabel(feature: string) {
  return `Customer attribute ${Number(feature.slice(1)) + 1}`;
}

function operationLabel(operation: TransformOperation) {
  return operation === "scale_percent" ? "Change by percentage" : "Shift by fixed amount";
}

function statusLabel(status: string) {
  if (status === "queued") return "Preparing the simulation";
  if (status === "running") return "Generating test data";
  if (status === "succeeded") return "Simulation ready";
  if (status === "expired") return "Download period ended";
  if (status === "failed") return "Simulation could not be completed";
  return "Waiting for an update";
}

function severityLabel(severity: string) {
  return severity === "high" ? "Large change" : severity === "medium" ? "Moderate change" : "Small change";
}

export function DriftSimulatorPanel() {
  const [preset, setPreset] = useState<Preset>("medium");
  const [rows, setRows] = useState(10000);
  const [advanced, setAdvanced] = useState<Record<string, Transformation>>(DEFAULT_ADVANCED);
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [simulation, setSimulation] = useState<DriftSimulation | null>(null);
  const [recent, setRecent] = useState<DriftSimulation[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const loadRecent = useCallback(async () => {
    const response = await fetch("/api/simulations?limit=5", { cache: "no-store" });
    if (response.ok) {
      const payload = await response.json();
      setRecent(payload.items ?? []);
    }
  }, []);

  useEffect(() => {
    loadRecent().catch(() => undefined);
  }, [loadRecent]);

  useEffect(() => {
    if (!simulation || !["queued", "running"].includes(simulation.status)) return;
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/simulations/${simulation.simulation_id}`, { cache: "no-store" });
        const payload = await response.json();
        if (response.ok) setSimulation(payload);
      } catch {
        // The next poll can recover from a transient network interruption.
      }
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [simulation]);

  const selectedTransformations = useMemo(
    () => FEATURES.filter((feature) => enabled[feature]).map((feature) => advanced[feature]),
    [advanced, enabled],
  );

  const updateTransformation = (feature: string, patch: Partial<Transformation>) => {
    setAdvanced((current) => ({ ...current, [feature]: { ...current[feature], ...patch } }));
  };

  const submit = async () => {
    setBusy(true);
    setMessage("");
    try {
      const body = preset === "advanced"
        ? { preset: null, rows, transformations: selectedTransformations }
        : { preset, rows };
      const response = await fetch("/api/simulations", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(safeError(payload, "The simulator could not be started."));
      setSimulation(payload);
      await loadRecent();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "The simulator could not be started.");
    } finally {
      setBusy(false);
    }
  };

  return <Panel className="wide drift-simulator-panel">
    <PanelHeading eyebrow="DRIFT SIMULATOR" title="Create a safe test scenario" />
    <p className="panel-description">Generate synthetic customer data with controlled changes. This does not change production data, retrain a model, or create a production drift report.</p>
    {message && <StatusMessage kind="error">{message}</StatusMessage>}
    <div className="simulator-form">
      <label>How strong should the test change be?
        <select value={preset} onChange={(event) => setPreset(event.target.value as Preset)}>
          <option value="low">Small change — a gentle shift</option>
          <option value="medium">Moderate change — a clear demo</option>
          <option value="high">Large change — an obvious shift</option>
          <option value="advanced">Choose attributes myself</option>
        </select>
      </label>
      <label>Number of test records
        <input type="number" min={100} max={100000} step={100} value={rows} onChange={(event) => setRows(Number(event.target.value))} />
        <small className="muted">The original reference data remains unchanged.</small>
      </label>
    </div>
    {preset === "advanced" && <details className="advanced-section" open>
      <summary>Choose which customer attributes change</summary>
      <p className="small muted">Enable an attribute, then choose whether to change it by percentage or by a fixed amount.</p>
      <div className="simulation-feature-list">{FEATURES.map((feature) => <div className="simulation-feature" key={feature}>
        <label className="feature-toggle"><input type="checkbox" checked={Boolean(enabled[feature])} onChange={(event) => setEnabled((current) => ({ ...current, [feature]: event.target.checked }))} /><span>{featureLabel(feature)}</span></label>
        <select aria-label={`${featureLabel(feature)} change type`} disabled={!enabled[feature]} value={advanced[feature].operation} onChange={(event) => updateTransformation(feature, { operation: event.target.value as TransformOperation })}>
          <option value="scale_percent">Change by percentage</option>
          <option value="shift">Shift by fixed amount</option>
        </select>
        <input aria-label={`${featureLabel(feature)} intensity`} disabled={!enabled[feature]} type="number" min={-100} max={100} step="any" value={advanced[feature].value} onChange={(event) => updateTransformation(feature, { value: Number(event.target.value) })} />
      </div>)}</div>
    </details>}
    <button className="primary action-button" disabled={busy || (preset === "advanced" && selectedTransformations.length === 0)} onClick={submit}>{busy ? "Starting…" : "Run test scenario"}</button>
    {simulation && <SimulationResult simulation={simulation} />}
    {!simulation && recent.length > 0 && <div className="recent-simulations"><span className="eyebrow">RECENT TEST SCENARIOS</span>{recent.map((item) => <button className="recent-simulation" key={item.simulation_id} onClick={() => setSimulation(item)}><span>{item.summary ? `${item.summary.affected_feature_count} attributes changed` : statusLabel(item.status)}</span><small className="muted">{formatTime(item.created_at)}</small></button>)}</div>}
  </Panel>;
}

function SimulationResult({ simulation }: { simulation: DriftSimulation }) {
  if (simulation.status === "failed") return <StatusMessage kind="error"><strong>{statusLabel(simulation.status)}</strong><br />Try a smaller test scenario or check that the reference data is available.</StatusMessage>;
  if (simulation.status === "expired") return <StatusMessage kind="warning"><strong>{statusLabel(simulation.status)}</strong><br />Run the scenario again to create a fresh download.</StatusMessage>;
  if (!simulation.summary) return <div className="simulation-progress" role="status"><span className="loading-spinner" /><div><strong>{statusLabel(simulation.status)}</strong><p className="small muted">The result will appear here when the test data is ready.</p></div></div>;
  return <div className="simulation-result" aria-live="polite">
    <div className="simulation-result-heading"><div><span className="eyebrow">TEST DATA SUMMARY</span><h3>{severityLabel(simulation.summary.severity)}</h3></div><span className="pill">Synthetic data</span></div>
    <p className="small muted">This is a controlled test scenario, separate from the production drift signal.</p>
    <div className="result-grid"><div><span className="muted">Records created</span><strong>{formatNumber(simulation.summary.rows, 0)}</strong></div><div><span className="muted">Attributes changed</span><strong>{simulation.summary.affected_feature_count}</strong></div><div><span className="muted">Created</span><strong>{formatTime(simulation.created_at)}</strong></div><div><span className="muted">Download available until</span><strong>{formatTime(simulation.expires_at)}</strong></div></div>
    <div className="simulation-feature-summary">{simulation.summary.affected_features.map((item) => <div className="simulation-summary-row" key={item.feature}><span><strong>{featureLabel(item.feature)}</strong><small className="muted">{operationLabel(item.operation)} · {item.value > 0 ? "+" : ""}{formatNumber(item.value)}{item.operation === "scale_percent" ? "%" : " units"}</small></span><span className="muted">{formatNumber(item.before_mean)} → {formatNumber(item.after_mean)} average</span></div>)}</div>
    <div className="download-actions">{simulation.downloads?.map((download) => <a className="secondary" href={download.url} key={download.format} download>{download.format === "parquet" ? "Download Parquet" : "Download CSV"}</a>)}</div>
  </div>;
}
