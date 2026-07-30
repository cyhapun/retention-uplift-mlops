export const DEMO_HISTORY_VERSION = 1;
export const DEMO_HISTORY_STORAGE_KEY = "retentionops.demo-history.v1";

export const HISTORY_LIMITS = {
  decisions: 50,
  feedback: 50,
  simulations: 20,
  predictions: 20,
} as const;

export type DemoDecisionSummary = {
  decisionId: string;
  userReference: string;
  createdAt: string;
  customerValue: number;
  recommendedAction: string;
  uplift: number;
  expectedValue: number;
  roi: number;
};

export type DemoFeedbackSummary = {
  feedbackId: string;
  decisionId: string;
  createdAt: string;
  outcome: "retained" | "not_retained";
  probability: number;
  realizedValue: number;
  delayDays: number;
};

export type DemoSimulationSummary = {
  simulationId: string;
  createdAt: string;
  status: string;
  rows: number;
  affectedFeatureCount: number;
  severity?: string;
  expiresAt?: string;
  hasDownload?: boolean;
};

export type DemoPredictionSummary = {
  predictionId: string;
  simulationId: string;
  createdAt: string;
  rows: number;
  mode: "model_only" | "policy_comparison";
  upliftDelta: number;
  expectedValueDelta?: number | null;
  roiDelta?: number | null;
  recommendationChangedCount?: number | null;
  recommendationChangedShare?: number | null;
  expiresAt?: string;
  hasDownload?: boolean;
};

export type DemoHistoryState = {
  version: typeof DEMO_HISTORY_VERSION;
  decisions: DemoDecisionSummary[];
  feedback: DemoFeedbackSummary[];
  simulations: DemoSimulationSummary[];
  predictions: DemoPredictionSummary[];
};

export type HistoryReadResult = {
  state: DemoHistoryState;
  warning?: string;
};

export type HistoryWriteResult = {
  ok: boolean;
  warning?: string;
};

export function emptyDemoHistory(): DemoHistoryState {
  return { version: DEMO_HISTORY_VERSION, decisions: [], feedback: [], simulations: [], predictions: [] };
}

export function demoLocalHistoryEnabled(): boolean {
  return process.env.NEXT_PUBLIC_DEMO_LOCAL_HISTORY !== "false";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function validDecision(value: unknown): value is DemoDecisionSummary {
  return isRecord(value) && isString(value.decisionId) && isString(value.userReference) && isString(value.createdAt)
    && isNumber(value.customerValue)
    && isString(value.recommendedAction) && isNumber(value.uplift) && isNumber(value.expectedValue) && isNumber(value.roi);
}

function validFeedback(value: unknown): value is DemoFeedbackSummary {
  return isRecord(value) && isString(value.feedbackId) && isString(value.decisionId) && isString(value.createdAt)
    && (value.outcome === "retained" || value.outcome === "not_retained") && isNumber(value.probability)
    && isNumber(value.realizedValue) && isNumber(value.delayDays);
}

function validSimulation(value: unknown): value is DemoSimulationSummary {
  return isRecord(value) && isString(value.simulationId) && isString(value.createdAt) && isString(value.status)
    && isNumber(value.rows) && isNumber(value.affectedFeatureCount);
}

function validPrediction(value: unknown): value is DemoPredictionSummary {
  return isRecord(value) && isString(value.predictionId) && isString(value.simulationId) && isString(value.createdAt)
    && isNumber(value.rows) && (value.mode === "model_only" || value.mode === "policy_comparison") && isNumber(value.upliftDelta);
}

function bounded<T>(items: T[], limit: number): T[] {
  return items.slice(0, limit);
}

function sanitize(state: DemoHistoryState): DemoHistoryState {
  return {
    version: DEMO_HISTORY_VERSION,
    decisions: bounded(state.decisions.filter(validDecision), HISTORY_LIMITS.decisions),
    feedback: bounded(state.feedback.filter(validFeedback), HISTORY_LIMITS.feedback),
    simulations: bounded(state.simulations.filter(validSimulation), HISTORY_LIMITS.simulations),
    predictions: bounded(state.predictions.filter(validPrediction), HISTORY_LIMITS.predictions),
  };
}

export function readDemoHistory(): HistoryReadResult {
  if (typeof window === "undefined" || !window.localStorage) return { state: emptyDemoHistory() };
  try {
    const raw = window.localStorage.getItem(DEMO_HISTORY_STORAGE_KEY);
    if (!raw) return { state: emptyDemoHistory() };
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed) || parsed.version !== DEMO_HISTORY_VERSION) {
      window.localStorage.removeItem(DEMO_HISTORY_STORAGE_KEY);
      return { state: emptyDemoHistory(), warning: "Older demo history was cleared because its format is no longer supported." };
    }
    return {
      state: sanitize({
        version: DEMO_HISTORY_VERSION,
        decisions: Array.isArray(parsed.decisions) ? parsed.decisions : [],
        feedback: Array.isArray(parsed.feedback) ? parsed.feedback : [],
        simulations: Array.isArray(parsed.simulations) ? parsed.simulations : [],
        predictions: Array.isArray(parsed.predictions) ? parsed.predictions : [],
      }),
    };
  } catch {
    try { window.localStorage.removeItem(DEMO_HISTORY_STORAGE_KEY); } catch { /* storage may be unavailable */ }
    return { state: emptyDemoHistory(), warning: "Browser history could not be read and was reset safely." };
  }
}

export function writeDemoHistory(state: DemoHistoryState): HistoryWriteResult {
  if (typeof window === "undefined" || !window.localStorage) return { ok: false, warning: "Browser history is unavailable in this environment." };
  let next = sanitize(state);
  try {
    let serialized = JSON.stringify(next);
    const collections: Array<keyof Omit<DemoHistoryState, "version">> = ["decisions", "feedback", "simulations", "predictions"];
    while (serialized.length > 200_000 && (next.decisions.length || next.feedback.length || next.simulations.length || next.predictions.length)) {
      const largest = [...collections].sort((a, b) => next[b].length - next[a].length)[0];
      next = { ...next, [largest]: next[largest].slice(0, -1) };
      serialized = JSON.stringify(next);
    }
    window.localStorage.setItem(DEMO_HISTORY_STORAGE_KEY, serialized);
    window.dispatchEvent(new CustomEvent("retentionops:demo-history-changed"));
    return { ok: true };
  } catch {
    return { ok: false, warning: "Browser storage quota is full or unavailable. The current result remains visible, but it was not added to history." };
  }
}

export function clearDemoHistory(collection?: keyof Omit<DemoHistoryState, "version">): HistoryWriteResult {
  if (typeof window === "undefined" || !window.localStorage) return { ok: false, warning: "Browser history is unavailable in this environment." };
  const current = readDemoHistory().state;
  const next = collection ? { ...current, [collection]: [] } : emptyDemoHistory();
  return writeDemoHistory(next);
}
