"use client";

import { FormEvent, useState } from "react";

import { FEATURE_LABELS, actionLabel, formatNumber, reasonLabel, safeError } from "./presentation";
import { Panel, PanelHeading, StatusMessage, TechnicalDetails } from "./control-center-shell";
import { useDemoLocalHistory } from "../hooks/use-demo-local-history";

const features = Array.from({ length: 11 }, (_, index) => `f${index}`);

type Decision = {
  decision_id: string;
  user_id: string;
  treatment_probability: number;
  control_probability: number;
  uplift_score: number;
  customer_value: number;
  treatment_cost: number;
  expected_incremental_value: number;
  roi: number;
  recommended_action: string;
  decision_reason: string[];
  model_name: string;
  model_alias: string;
  model_version: string;
};

export function DecisionForm({ modelReady, onCompleted }: { modelReady: boolean; onCompleted?: () => void }) {
  const [form, setForm] = useState({ userId: "demo_user_001", customerValue: "100" });
  const [featureValues, setFeatureValues] = useState<Record<string, string>>(Object.fromEntries(features.map((feature) => [feature, "0"])));
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { enabled, addDecision, warning } = useDemoLocalHistory();

  const submitDecision = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setDecision(null);
    try {
      const response = await fetch("/api/decisions", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          user_id: form.userId,
          customer_value: Number(form.customerValue),
          features: Object.fromEntries(features.map((feature) => [feature, Number(featureValues[feature])])),
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(safeError(payload, "The decision could not be completed."));
      setDecision(payload);
      if (enabled) {
        addDecision({
          decisionId: payload.decision_id,
          userReference: payload.user_id,
          createdAt: new Date().toISOString(),
          customerValue: payload.customer_value,
          recommendedAction: payload.recommended_action,
          uplift: payload.uplift_score,
          expectedValue: payload.expected_incremental_value,
          roi: payload.roi,
        });
      }
      onCompleted?.();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The decision could not be completed.");
    } finally {
      setBusy(false);
    }
  };

  return <Panel className="decision-panel">
    <PanelHeading eyebrow="DECISION WORKBENCH" title="Test a retention action" />
    <p className="panel-description">Enter a customer profile to see which retention action is expected to create the most value.</p>
    {!modelReady && <StatusMessage kind="warning">The champion model is not ready yet. Decision testing will be enabled when the model is available.</StatusMessage>}
    {error && <StatusMessage kind="error">{error}</StatusMessage>}
    {warning && <StatusMessage kind="warning">{warning}</StatusMessage>}
    <form onSubmit={submitDecision} className="form-stack">
      <label>Customer reference<input required value={form.userId} onChange={(event) => setForm({ ...form, userId: event.target.value })} aria-describedby="customer-reference-help" /></label>
      <p id="customer-reference-help" className="small muted">A reference used to find this decision later. It does not need to be a real name.</p>
      <label>Estimated customer value<input required type="number" min="0.01" step="0.01" value={form.customerValue} onChange={(event) => setForm({ ...form, customerValue: event.target.value })} aria-describedby="customer-value-help" /></label>
      <p id="customer-value-help" className="small muted">An assumption used to estimate ROI and expected value; it is not automatically observed by the model.</p>
      <details className="advanced-section" open>
        <summary>Advanced customer attributes</summary>
        <p className="small muted">These are model inputs. Their exact business meaning comes from the training data dictionary.</p>
        <div className="feature-grid">{features.map((feature) => <label key={feature}>{FEATURE_LABELS[feature].label}<input required type="number" step="any" value={featureValues[feature]} aria-label={`${FEATURE_LABELS[feature].label} (${feature})`} onChange={(event) => setFeatureValues({ ...featureValues, [feature]: event.target.value })} /><small>{feature}</small></label>)}</div>
      </details>
      <button className="primary action-button" disabled={busy || !modelReady}>{busy ? "Evaluating…" : "Run decision"}</button>
    </form>
    {decision && <div className="decision-result" aria-live="polite">
      <span className="eyebrow">RECOMMENDATION</span>
      <strong>{actionLabel(decision.recommended_action)}</strong>
      <p className="result-summary">This action has an estimated uplift of <b>{formatNumber(decision.uplift_score)}</b> and expected value of <b>{formatNumber(decision.expected_incremental_value)}</b>.</p>
      <div className="result-grid"><div><span className="muted">Estimated ROI</span><b>{formatNumber(decision.roi)}</b></div><div><span className="muted">Offer cost</span><b>{formatNumber(decision.treatment_cost)}</b></div><div><span className="muted">Treatment likelihood</span><b>{formatNumber(decision.treatment_probability)}</b></div><div><span className="muted">Control likelihood</span><b>{formatNumber(decision.control_probability)}</b></div></div>
      <div className="reason-list"><span className="muted">Why this recommendation</span>{decision.decision_reason.map((reason) => <span key={reason}>✓ {reasonLabel(reason)}</span>)}</div>
      <TechnicalDetails><p>Decision reference: <code>{decision.decision_id}</code></p><p>Model: {decision.model_name}@{decision.model_alias}</p><p>Model run reference: <code>{decision.model_version}</code></p></TechnicalDetails>
    </div>}
  </Panel>;
}
