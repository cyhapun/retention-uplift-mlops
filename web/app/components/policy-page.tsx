"use client";

import { useCallback, useEffect, useState } from "react";

import { ControlCenterShell, LoadingState, PageIntro, Panel, PanelHeading, StatusMessage, TechnicalDetails } from "./control-center-shell";
import { actionLabel, formatNumber, formatTime, safeError } from "./presentation";

type ActionRule = { cost: number; min_expected_value: number; min_uplift: number; priority: number };
type Policy = { actions: Record<string, ActionRule>; min_uplift_for_action: number; max_daily_budget: number };
type Snapshot = { version_id: string; version_number: number; created_at?: string; activated_at?: string; created_by: string; is_active?: boolean; editable: boolean; policy: Policy };
type Preview = { available: boolean; reason?: string; population: number; evaluation_period?: string; changed_decisions: number; estimated_action_distribution: Record<string, number>; estimated_average_expected_value?: number };
type History = { versions: Snapshot[]; audits: Array<{ audit_id: string; action: string; actor: string; status: string; outcome: string; created_at?: string }> };

function clonePolicy(policy: Policy): Policy {
  return JSON.parse(JSON.stringify(policy)) as Policy;
}

function PolicyVersionDetails({ version }: { version: Snapshot }) {
  return (
    <div className="policy-version-details">
      <div className="policy-version-summary">
        <span>Created by <strong>{version.created_by}</strong></span>
        <span>Activated {formatTime(version.activated_at)}</span>
      </div>
      <div className="policy-table">
        <div className="policy-table-head">
          <span>Action</span><span>Cost</span><span>Minimum uplift</span><span>Minimum value</span><span>Priority</span>
        </div>
        {Object.entries(version.policy.actions).map(([name, rule]) => (
          <div className="policy-table-row" key={name}>
            <strong>{actionLabel(name)}</strong>
            <span>{formatNumber(rule.cost)}</span>
            <span>{formatNumber(rule.min_uplift)}</span>
            <span>{formatNumber(rule.min_expected_value)}</span>
            <span>{rule.priority}</span>
          </div>
        ))}
      </div>
      <div className="policy-version-summary">
        <span>Minimum uplift before offering: <strong>{formatNumber(version.policy.min_uplift_for_action)}</strong></span>
        <span>Maximum daily budget: <strong>{formatNumber(version.policy.max_daily_budget)}</strong></span>
      </div>
    </div>
  );
}

export function PolicyPage() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [draft, setDraft] = useState<Policy | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const response = await fetch("/api/policy", { cache: "no-store" });
      const payload = await response.json() as Snapshot;
      if (!response.ok) throw new Error(safeError(payload, "The active policy could not be loaded."));
      setSnapshot(payload);
      setDraft(clonePolicy(payload.policy));
      setError("");
      if (payload.editable) {
        const historyResponse = await fetch("/api/policy/history", { cache: "no-store" });
        if (historyResponse.ok) setHistory(await historyResponse.json() as History);
      } else {
        setHistory(null);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The active policy could not be loaded.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const hasUnsavedChanges = Boolean(snapshot && draft && JSON.stringify(snapshot.policy) !== JSON.stringify(draft));
  useEffect(() => {
    if (!hasUnsavedChanges) return;
    const warnBeforeLeaving = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeLeaving);
    return () => window.removeEventListener("beforeunload", warnBeforeLeaving);
  }, [hasUnsavedChanges]);

  const updateAction = (name: string, field: keyof ActionRule, value: string) => {
    if (!draft) return;
    setDraft({ ...draft, actions: { ...draft.actions, [name]: { ...draft.actions[name], [field]: Number(value) } } });
    setMessage("");
  };

  const validate = async () => {
    if (!draft) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await fetch("/api/policy/validate", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(draft) });
      const payload = await response.json();
      if (!response.ok || !payload.valid) throw new Error(payload.errors?.join(" ") ?? safeError(payload, "The proposed policy is not valid."));
      setMessage("The proposed policy passed validation.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The proposed policy is not valid.");
    } finally {
      setBusy(false);
    }
  };

  const showPreview = async () => {
    if (!draft) return;
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/policy/preview", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ policy: draft }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(safeError(payload, "The policy preview could not be created."));
      setPreview(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The policy preview could not be created.");
    } finally {
      setBusy(false);
    }
  };

  const activate = async () => {
    if (!snapshot || !draft || !window.confirm("Activate this policy for new decisions?")) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await fetch("/api/policy/activate", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ policy: draft, expected_version_id: snapshot.version_id, confirm: true, change_summary: "Activated from the Control Center." }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(safeError(payload, "The policy could not be activated."));
      setMessage(`Policy version ${payload.version_number} is now active.`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The policy could not be activated.");
    } finally {
      setBusy(false);
    }
  };

  const rollback = async (versionId: string, versionNumber: number) => {
    if (!snapshot || !window.confirm(`Use policy version ${versionNumber} for new decisions?`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await fetch(`/api/policy/rollback/${versionId}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ expected_version_id: snapshot.version_id, confirm: true }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(safeError(payload, "The policy could not be rolled back."));
      setMessage(`Policy version ${payload.version_number} is active again.`);
      setSelectedVersionId(null);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The policy could not be rolled back.");
    } finally {
      setBusy(false);
    }
  };

  const deleteVersion = async (versionId: string, versionNumber: number) => {
    if (!snapshot || !window.confirm(`Delete policy version ${versionNumber}? This cannot be undone.`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await fetch(`/api/policy/versions/${versionId}`, { method: "DELETE", headers: { "content-type": "application/json" }, body: JSON.stringify({ expected_version_id: snapshot.version_id, confirm: true }) });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(safeError(payload, "The policy version could not be deleted."));
      }
      setMessage(`Policy version ${versionNumber} was deleted.`);
      setSelectedVersionId(null);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The policy version could not be deleted.");
    } finally {
      setBusy(false);
    }
  };

  if (!snapshot && busy) return <ControlCenterShell active="/policy"><LoadingState label="Loading the active policy..." /></ControlCenterShell>;

  return (
    <ControlCenterShell active="/policy" environment="policy" onRefresh={load} refreshing={busy}>
      <PageIntro eyebrow="POLICY" title="Keep decision rules understandable and controlled." description="Review the active thresholds, preview their likely impact, and activate changes only when they are validated and authorized." />
      {error && <StatusMessage kind="error">{error}</StatusMessage>}
      {message && <StatusMessage kind="success">{message}</StatusMessage>}
      <div className="policy-meta">
        <span>Active version <b>{snapshot?.version_number ?? "-"}</b></span>
        <span>Activated {formatTime(snapshot?.activated_at)}</span>
        <span>Owner {snapshot?.created_by ?? "-"}</span>
        {snapshot?.editable ? <span className="editable-badge">Editing enabled</span> : <span className="readonly-badge">Read-only mode</span>}
      </div>
      <div className="content-grid two-column">
        <Panel>
          <PanelHeading eyebrow="ACTIVE POLICY" title="Decision rules" />
          <p className="panel-description">Costs are expressed in value units. Uplift is a model score from 0 to 1. An action must meet both its uplift and expected-value thresholds.</p>
          <div className="policy-table">
            <div className="policy-table-head"><span>Action</span><span>Cost</span><span>Min. uplift</span><span>Min. expected value</span><span>Priority</span></div>
            {draft && Object.entries(draft.actions).map(([name, rule]) => <div className="policy-table-row" key={name}><strong>{actionLabel(name)}</strong><input aria-label={`${actionLabel(name)} cost`} type="number" min="0" step=".01" value={rule.cost} disabled={!snapshot?.editable} onChange={(event) => updateAction(name, "cost", event.target.value)} /><input aria-label={`${actionLabel(name)} minimum uplift`} type="number" min="0" max="1" step=".01" value={rule.min_uplift} disabled={!snapshot?.editable} onChange={(event) => updateAction(name, "min_uplift", event.target.value)} /><input aria-label={`${actionLabel(name)} minimum expected value`} type="number" min="0" step=".01" value={rule.min_expected_value} disabled={!snapshot?.editable} onChange={(event) => updateAction(name, "min_expected_value", event.target.value)} /><input aria-label={`${actionLabel(name)} priority`} type="number" min="0" step="1" value={rule.priority} disabled={!snapshot?.editable} onChange={(event) => updateAction(name, "priority", event.target.value)} /></div>)}
          </div>
          <div className="global-policy-fields"><label>Minimum uplift before offering<input type="number" min="0" max="1" step=".01" value={draft?.min_uplift_for_action ?? 0} disabled={!snapshot?.editable} onChange={(event) => draft && setDraft({ ...draft, min_uplift_for_action: Number(event.target.value) })} /></label><label>Maximum daily budget<input type="number" min="0" step=".01" value={draft?.max_daily_budget ?? 0} disabled={!snapshot?.editable} onChange={(event) => draft && setDraft({ ...draft, max_daily_budget: Number(event.target.value) })} /></label></div>
          {snapshot?.editable && <div className="policy-actions"><button className="secondary" disabled={busy} onClick={validate}>Validate changes</button><button className="secondary" disabled={busy} onClick={showPreview}>Preview impact</button><button className="primary" disabled={busy} onClick={activate}>Activate policy</button></div>}
          <TechnicalDetails title="What does this control?"><p>{snapshot?.editable ? "Changes are stored as policy versions in PostgreSQL. In this demo, inactive versions can be viewed, reused, or deleted." : "Editing is disabled because the policy store or admin authorization is not configured. The YAML policy is being shown as a safe fallback."}</p></TechnicalDetails>
        </Panel>
        <Panel>
          <PanelHeading eyebrow="IMPACT PREVIEW" title="Before you activate" />
          {preview ? preview.available ? <><div className="preview-summary"><div><span className="muted">Decisions reviewed</span><strong>{preview.population}</strong></div><div><span className="muted">Recommendations changed</span><strong>{preview.changed_decisions}</strong></div><div><span className="muted">Average expected value</span><strong>{formatNumber(preview.estimated_average_expected_value)}</strong></div></div><p className="small muted">Estimate period: {preview.evaluation_period ?? "Not available"}</p><div className="reason-list"><span className="muted">Estimated action mix</span>{Object.entries(preview.estimated_action_distribution).map(([name, count]) => <span key={name}>{actionLabel(name)}: {count}</span>)}</div></> : <StatusMessage kind="info">{preview.reason ?? "There is not enough history for an estimate yet."}</StatusMessage> : <p className="muted">Validate a draft, then preview how it would have changed recent logged decisions.</p>}
          <div className="history-heading"><PanelHeading eyebrow="VERSION HISTORY" title="Review and manage versions" /></div>
          {history?.versions?.length ? history.versions.map((version) => {
            const isActive = version.version_id === snapshot?.version_id;
            const isSelected = selectedVersionId === version.version_id;
            return <div className="policy-version-row" key={version.version_id}>
              <div className="policy-version-heading"><strong>Version {version.version_number}{isActive ? " (active)" : ""}</strong><small className="muted">{formatTime(version.activated_at)} · {version.created_by}</small></div>
              <div className="policy-version-actions">
                <button className="secondary" disabled={busy} onClick={() => setSelectedVersionId(isSelected ? null : version.version_id)}>{isSelected ? "Hide rules" : "View rules"}</button>
                {!isActive && <><button className="secondary" disabled={busy} onClick={() => rollback(version.version_id, version.version_number)}>Use this version</button><button className="secondary danger-button" disabled={busy} onClick={() => deleteVersion(version.version_id, version.version_number)}>Delete</button></>}
              </div>
              {isSelected && <PolicyVersionDetails version={version} />}
            </div>;
          }) : <p className="muted">Version history is available to administrators when policy persistence is enabled.</p>}
        </Panel>
      </div>
    </ControlCenterShell>
  );
}
