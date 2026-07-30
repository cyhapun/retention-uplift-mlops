"use client";

import { useCallback, useEffect, useState } from "react";

import {
  DemoDecisionSummary,
  DemoFeedbackSummary,
  DemoHistoryState,
  DemoPredictionSummary,
  DemoSimulationSummary,
  demoLocalHistoryEnabled,
  emptyDemoHistory,
  readDemoHistory,
  writeDemoHistory,
} from "../lib/demo-local-history";

export function useDemoLocalHistory() {
  const enabled = demoLocalHistoryEnabled();
  const [history, setHistory] = useState<DemoHistoryState>(emptyDemoHistory);
  const [hydrated, setHydrated] = useState(false);
  const [warning, setWarning] = useState("");

  const refresh = useCallback(() => {
    if (!enabled) { setHydrated(true); return; }
    const result = readDemoHistory();
    setHistory(result.state);
    setWarning(result.warning ?? "");
    setHydrated(true);
  }, [enabled]);

  useEffect(() => {
    refresh();
    const handler = () => refresh();
    window.addEventListener("retentionops:demo-history-changed", handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener("retentionops:demo-history-changed", handler);
      window.removeEventListener("storage", handler);
    };
  }, [refresh]);

  const update = useCallback((next: DemoHistoryState) => {
    const result = writeDemoHistory(next);
    setWarning(result.warning ?? "");
    if (result.ok) setHistory(next);
    return result;
  }, []);

  const addDecision = useCallback((item: DemoDecisionSummary) => update({ ...history, decisions: [item, ...history.decisions] }), [history, update]);
  const addFeedback = useCallback((item: DemoFeedbackSummary) => update({ ...history, feedback: [item, ...history.feedback] }), [history, update]);
  const addFeedbackBatch = useCallback((items: DemoFeedbackSummary[]) => update({ ...history, feedback: [...items, ...history.feedback] }), [history, update]);
  const addSimulation = useCallback((item: DemoSimulationSummary) => update({ ...history, simulations: [item, ...history.simulations] }), [history, update]);
  const addPrediction = useCallback((item: DemoPredictionSummary) => update({ ...history, predictions: [item, ...history.predictions] }), [history, update]);

  const clear = useCallback((collection?: keyof Omit<DemoHistoryState, "version">) => {
    const next = collection ? { ...history, [collection]: [] } : emptyDemoHistory();
    return update(next);
  }, [history, update]);
  const clearCollections = useCallback((collections: Array<keyof Omit<DemoHistoryState, "version">>) => {
    const next = { ...history };
    for (const collection of collections) next[collection] = [];
    return update(next);
  }, [history, update]);

  return { enabled, hydrated, history, warning, refresh, addDecision, addFeedback, addFeedbackBatch, addSimulation, addPrediction, clear, clearCollections };
}
