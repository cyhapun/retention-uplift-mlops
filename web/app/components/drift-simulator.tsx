"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Panel, PanelHeading, StatusMessage } from "./control-center-shell";
import { formatNumber, formatPercent, formatTime, safeError } from "./presentation";
import { useDemoLocalHistory } from "../hooks/use-demo-local-history";

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

type PredictionMode = "model_only" | "policy_comparison";
type PredictionSummary = {
  mode: PredictionMode;
  rows: number;
  baseline_average_uplift: number;
  simulated_average_uplift: number;
  uplift_delta: number;
  customer_value?: number | null;
  recommendation_changed_count?: number | null;
  recommendation_changed_share?: number | null;
  baseline_action_distribution: Record<string, number>;
  simulated_action_distribution: Record<string, number>;
  baseline_average_expected_value?: number | null;
  simulated_average_expected_value?: number | null;
  expected_value_delta?: number | null;
  baseline_average_roi?: number | null;
  simulated_average_roi?: number | null;
  roi_delta?: number | null;
};

type Prediction = {
  prediction_id: string;
  status: string;
  request: { mode: PredictionMode; customer_value?: number | null };
  summary?: PredictionSummary | null;
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

export function DriftSimulatorPanel({ modelReady }: { modelReady?: boolean }) {
  if (modelReady === undefined) return <Panel className="wide"><PanelHeading eyebrow="SAFE TESTING" title="Explore a what-if scenario" /><p className="panel-description">Create synthetic drift and compare how the champion model responds in Simulation Lab. Test data stays separate from production monitoring.</p><a className="secondary" href="/simulation-lab">Open Simulation Lab ↗</a></Panel>;
  const [preset, setPreset] = useState<Preset>("medium");
  const [rows, setRows] = useState(10000);
  const [advanced, setAdvanced] = useState<Record<string, Transformation>>(DEFAULT_ADVANCED);
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [simulation, setSimulation] = useState<DriftSimulation | null>(null);
  const [recent, setRecent] = useState<DriftSimulation[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [predictionMode, setPredictionMode] = useState<PredictionMode>("model_only");
  const [customerValue, setCustomerValue] = useState("100");
  const [predictionBusy, setPredictionBusy] = useState(false);
  const [predictionMessage, setPredictionMessage] = useState("");
  const { enabled: localHistoryEnabled, history, addSimulation, addPrediction, clearCollections } = useDemoLocalHistory();

  const loadRecent = useCallback(async () => {
    if (localHistoryEnabled) return;
    const response = await fetch("/api/simulations?limit=5", { cache: "no-store" });
    if (response.ok) {
      const payload = await response.json();
      setRecent(payload.items ?? []);
    }
  }, [localHistoryEnabled]);

  useEffect(() => {
    if (!localHistoryEnabled || !simulation || simulation.status !== "succeeded" || !simulation.summary) return;
    if (history.simulations.some((item) => item.simulationId === simulation.simulation_id)) return;
    addSimulation({
      simulationId: simulation.simulation_id,
      createdAt: simulation.created_at ?? new Date().toISOString(),
      status: simulation.status,
      rows: simulation.summary.rows,
      affectedFeatureCount: simulation.summary.affected_feature_count,
      severity: simulation.summary.severity,
      expiresAt: simulation.expires_at,
      hasDownload: Boolean(simulation.downloads?.length),
    });
  }, [addSimulation, history.simulations, localHistoryEnabled, simulation]);

  useEffect(() => {
    if (!localHistoryEnabled || !prediction || prediction.status !== "succeeded" || !prediction.summary) return;
    if (history.predictions.some((item) => item.predictionId === prediction.prediction_id)) return;
    addPrediction({
      predictionId: prediction.prediction_id,
      simulationId: simulation?.simulation_id ?? "unknown",
      createdAt: prediction.created_at ?? new Date().toISOString(),
      rows: prediction.summary.rows,
      mode: prediction.summary.mode,
      upliftDelta: prediction.summary.uplift_delta,
      expectedValueDelta: prediction.summary.expected_value_delta,
      roiDelta: prediction.summary.roi_delta,
      recommendationChangedCount: prediction.summary.recommendation_changed_count,
      recommendationChangedShare: prediction.summary.recommendation_changed_share,
      expiresAt: prediction.expires_at,
      hasDownload: Boolean(prediction.downloads?.length),
    });
  }, [addPrediction, history.predictions, localHistoryEnabled, prediction, simulation?.simulation_id]);

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

  useEffect(() => {
    if (!prediction || !["queued", "running"].includes(prediction.status)) return;
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/simulation-predictions/${prediction.prediction_id}`, { cache: "no-store" });
        const payload = await response.json();
        if (response.ok) setPrediction(payload);
      } catch {
        // The next poll can recover from a transient network interruption.
      }
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [prediction]);

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
      setPrediction(null);
      await loadRecent();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "The simulator could not be started.");
    } finally {
      setBusy(false);
    }
  };

  const runPrediction = async () => {
    if (!simulation || simulation.status !== "succeeded") return;
    setPredictionBusy(true);
    setPredictionMessage("");
    try {
      const body = predictionMode === "policy_comparison"
        ? { mode: predictionMode, customer_value: Number(customerValue) }
        : { mode: predictionMode };
      const response = await fetch(`/api/simulations/${simulation.simulation_id}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(safeError(payload, "The model comparison could not be started."));
      setPrediction(payload);
    } catch (caught) {
      setPredictionMessage(caught instanceof Error ? caught.message : "The model comparison could not be started.");
    } finally {
      setPredictionBusy(false);
    }
  };

  return <Panel className="wide drift-simulator-panel">
    <PanelHeading eyebrow="SIMULATION LAB" title="Create a safe what-if scenario" />
    <p className="panel-description">Generate synthetic customer data with controlled changes, then see how the champion model responds. This never changes production data, decisions, feedback, retraining, or drift reports.</p>
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
    {simulation?.status === "succeeded" && <PredictionPanel modelReady={modelReady} mode={predictionMode} setMode={setPredictionMode} customerValue={customerValue} setCustomerValue={setCustomerValue} busy={predictionBusy} message={predictionMessage} prediction={prediction} onRun={runPrediction} />}
    {localHistoryEnabled && <div className="history-actions"><button className="text-button" onClick={() => { if (window.confirm("Clear Simulation Lab history?")) clearCollections(["simulations", "predictions"]); }}>Clear history</button></div>}
    {!simulation && recent.length > 0 && <div className="recent-simulations"><span className="eyebrow">RECENT TEST SCENARIOS</span>{recent.map((item) => <button className="recent-simulation" key={item.simulation_id} onClick={() => setSimulation(item)}><span>{item.summary ? `${item.summary.affected_feature_count} attributes changed` : statusLabel(item.status)}</span><small className="muted">{formatTime(item.created_at)}</small></button>)}</div>}
    {!simulation && localHistoryEnabled && history.simulations.length > 0 && <div className="recent-simulations"><span className="eyebrow">RECENT TESTS</span>{history.simulations.slice(0, 5).map((item) => <div className="recent-simulation" key={item.simulationId}><span>{item.severity ? severityLabel(item.severity) : statusLabel(item.status)} · {formatNumber(item.affectedFeatureCount, 0)} attributes changed</span><small className="muted">{formatTime(item.createdAt)} · {item.hasDownload && item.expiresAt && new Date(item.expiresAt) > new Date() ? "Download available" : "Summary only"}</small></div>)}</div>}
    {!simulation && localHistoryEnabled && history.predictions.length > 0 && <div className="recent-simulations"><span className="eyebrow">RECENT PREDICTION COMPARISONS</span>{history.predictions.slice(0, 5).map((item) => <div className="recent-simulation" key={item.predictionId}><span>{item.mode === "policy_comparison" ? "Recommendation comparison" : "Model response"}</span><small className="muted">{formatNumber(item.rows, 0)} paired records · uplift change {formatNumber(item.upliftDelta)}</small></div>)}</div>}
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

function PredictionPanel({
  modelReady,
  mode,
  setMode,
  customerValue,
  setCustomerValue,
  busy,
  message,
  prediction,
  onRun,
}: {
  modelReady: boolean;
  mode: PredictionMode;
  setMode: (mode: PredictionMode) => void;
  customerValue: string;
  setCustomerValue: (value: string) => void;
  busy: boolean;
  message: string;
  prediction: Prediction | null;
  onRun: () => void;
}) {
  return <div className="prediction-workspace">
    <div className="prediction-heading"><div><span className="eyebrow">MODEL COMPARISON</span><h3>What changed for the champion model?</h3></div><span className={`pill ${modelReady ? "success" : "warning"}`}>{modelReady ? "Model ready" : "Model unavailable"}</span></div>
    <p className="small muted">The same synthetic rows are scored before and after the scenario so the result shows the effect of the change, not a production outcome.</p>
    <div className="prediction-controls">
      <label>Comparison type
        <select value={mode} onChange={(event) => setMode(event.target.value as PredictionMode)} disabled={!modelReady || Boolean(prediction && ["queued", "running"].includes(prediction.status))}>
          <option value="model_only">Model-only comparison</option>
          <option value="policy_comparison">Include recommendation comparison</option>
        </select>
        <small className="muted">Model-only mode compares predicted uplift. Recommendation comparison also applies the current policy.</small>
      </label>
      {mode === "policy_comparison" && <label>Illustrative customer value
        <input type="number" min="0.01" step="any" value={customerValue} onChange={(event) => setCustomerValue(event.target.value)} disabled={!modelReady} />
        <small className="muted">This is a business assumption for the test only; it is not learned from the data.</small>
      </label>}
    </div>
    {!modelReady && <StatusMessage kind="warning">The champion model is not ready. Prepare a registered model before running a comparison.</StatusMessage>}
    {message && <StatusMessage kind="error">{message}</StatusMessage>}
    <button className="primary action-button" disabled={!modelReady || busy || Boolean(prediction && ["queued", "running"].includes(prediction.status))} onClick={onRun}>{busy ? "Starting comparison…" : prediction && ["queued", "running"].includes(prediction.status) ? "Scoring synthetic rows…" : "Run model comparison"}</button>
    {prediction && <PredictionResult prediction={prediction} />}
  </div>;
}

function PredictionResult({ prediction }: { prediction: Prediction }) {
  if (["queued", "running"].includes(prediction.status)) return <div className="simulation-progress" role="status"><span className="loading-spinner" /><div><strong>{prediction.status === "queued" ? "Comparison queued" : "Scoring synthetic rows"}</strong><p className="small muted">The result will appear here when both datasets have been scored.</p></div></div>;
  if (prediction.status === "failed") return <StatusMessage kind="error"><strong>Comparison could not be completed.</strong><br />{predictionErrorLabel(prediction.error_summary)}</StatusMessage>;
  if (prediction.status === "expired") return <StatusMessage kind="warning"><strong>Comparison download period ended.</strong><br />Run the comparison again to create a fresh result.</StatusMessage>;
  if (!prediction.summary) return <StatusMessage kind="info">The comparison is ready, but no summary is available yet.</StatusMessage>;
  const summary = prediction.summary;
  return <div className="prediction-result" aria-live="polite">
    <div className="prediction-heading"><div><span className="eyebrow">PREDICTION RESULT</span><h3>{summary.mode === "policy_comparison" ? "Model and recommendation comparison" : "Model-only comparison"}</h3></div><span className="pill">Synthetic result</span></div>
    <p className="small muted">{formatNumber(summary.rows, 0)} paired test records. Available until {formatTime(prediction.expires_at)}.</p>
    <div className="comparison-grid"><ComparisonMetric label="Average uplift" before={summary.baseline_average_uplift} after={summary.simulated_average_uplift} delta={summary.uplift_delta} /><ComparisonMetric label="Expected value" before={summary.baseline_average_expected_value} after={summary.simulated_average_expected_value} delta={summary.expected_value_delta} /><ComparisonMetric label="ROI" before={summary.baseline_average_roi} after={summary.simulated_average_roi} delta={summary.roi_delta} percent /></div>
    <div className="comparison-table" role="table" aria-label="Before and after comparison"><div className="comparison-table-row comparison-table-header" role="row"><span>Measure</span><span>Before</span><span>After</span><span>Change</span></div><ComparisonRow label="Average uplift" before={summary.baseline_average_uplift} after={summary.simulated_average_uplift} delta={summary.uplift_delta} /><ComparisonRow label="Expected value" before={summary.baseline_average_expected_value} after={summary.simulated_average_expected_value} delta={summary.expected_value_delta} /><ComparisonRow label="ROI" before={summary.baseline_average_roi} after={summary.simulated_average_roi} delta={summary.roi_delta} /></div>
    {summary.mode === "policy_comparison" && <><div className="change-callout"><strong>{formatNumber(summary.recommendation_changed_count, 0)} recommendations changed</strong><span>{formatPercent(summary.recommendation_changed_share)} of test records received a different recommendation.</span></div><div className="distribution-grid"><Distribution title="Before" values={summary.baseline_action_distribution} /><Distribution title="After" values={summary.simulated_action_distribution} /></div><p className="small muted">Customer value used: {formatNumber(summary.customer_value)}. This value is illustrative and only affects this comparison.</p></>}
    <div className="download-actions">{prediction.downloads?.map((download) => <a className="secondary" href={download.url} key={download.format} download>{download.format === "parquet" ? "Download result (Parquet)" : "Download result (CSV)"}</a>)}</div>
  </div>;
}

function predictionErrorLabel(error?: string | null) {
  if (!error) return "Check that the champion model is available and try again.";
  if (error.toLowerCase().includes("registered model") || error.toLowerCase().includes("model not found")) return "The champion model is not registered yet. Register a champion model in Operations, then try again.";
  if (error.toLowerCase().includes("customer value")) return "Enter a positive illustrative customer value for recommendation comparison.";
  return "The platform could not score this test scenario. Check model readiness and try again.";
}

function ComparisonRow({ label, before, after, delta }: { label: string; before?: number | null; after?: number | null; delta?: number | null }) {
  return <div className="comparison-table-row" role="row"><span>{label}</span><span>{formatNumber(before)}</span><span>{formatNumber(after)}</span><span>{delta == null ? "Not included" : `${delta >= 0 ? "+" : ""}${formatNumber(delta)}`}</span></div>;
}

function ComparisonMetric({ label, before, after, delta, percent = false }: { label: string; before?: number | null; after?: number | null; delta?: number | null; percent?: boolean }) {
  if (before == null || after == null || delta == null) return <div className="metric-card muted-metric"><span>{label}</span><strong>Not included</strong><small>Enable recommendation comparison to see this value.</small></div>;
  return <div className="metric-card"><span>{label}</span><strong>{formatNumber(after)}{percent ? "×" : ""}</strong><small>Before {formatNumber(before)} · Change {delta >= 0 ? "+" : ""}{formatNumber(delta)}</small></div>;
}

function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  return <div className="distribution"><strong>{title}</strong>{Object.entries(values).length ? Object.entries(values).map(([action, count]) => <div className="distribution-row" key={action}><span>{action.replaceAll("_", " ")}</span><b>{formatNumber(count, 0)}</b></div>) : <span className="muted">No recommendation data.</span>}</div>;
}
