## Context

The current browser calls the FastAPI decision endpoint and the operations control plane persists demo history in PostgreSQL. The existing Control Center also polls persisted Simulation Lab records and the delayed-feedback operation reads persisted decision logs. For a single-user Docker demo, this durable history is unnecessary: policy versions need to survive restarts, while demo results only need to survive a reload in the same browser.

The change must preserve the current model and policy behavior, avoid placing large prediction artifacts in browser storage, and make the demo boundary explicit so browser-local history is not mistaken for production audit data.

## Goals / Non-Goals

**Goals:**

- Add a versioned, bounded browser-local history for compact decision, feedback, and Simulation Lab summaries.
- Make demo decision/feedback/simulation history independent from durable PostgreSQL records.
- Keep `policy_versions` durable and continue using the existing protected policy APIs.
- Keep model inference and policy evaluation on the server; never move model artifacts or admin credentials into the browser.
- Preserve temporary Parquet/CSV downloads without copying their full contents into `localStorage`.
- Provide clear reload, empty, corrupted-storage, quota, and reset behavior.

**Non-Goals:**

- This is not a production audit, multi-user history, offline model-serving, or cross-device synchronization feature.
- This does not remove the existing PostgreSQL tables immediately; compatibility tables may remain unused in demo-local mode.
- This does not persist raw customer features, full decision logs, feedback logs, or large simulation rows in `localStorage`.
- This does not change the champion model, policy formulas, Prometheus metrics, or MLflow storage.

## Decisions

### Use a versioned localStorage store for compact summaries

Create one typed client-side history module with versioned keys/envelopes for decisions, feedback, and Simulation Lab results. Each collection has a maximum item count and serialized-size guard. Writes are best-effort: a quota or serialization failure must not make the primary decision or simulation result fail.

Store only display-safe summaries: opaque reference, created time, recommendation, uplift/value metrics, scenario mode, and bounded status. Do not store the full feature vector, raw logs, tokens, database credentials, or Parquet/CSV bytes.

### Hydrate only after client mount

Read `localStorage` inside client effects or a client store initializer after mount. Server-rendered pages must render a deterministic empty/loading state first, preventing hydration mismatch and browser API access during Next.js server rendering.

### Keep inference server-side and make demo persistence explicit

Add a demo-local persistence setting for the API/ops stack. In this mode the decision endpoint returns the model result but skips the durable decision log; the frontend immediately records the compact response locally. Delayed-feedback simulation operates on the local decision summaries and writes its simulated feedback summary locally instead of querying PostgreSQL.

Simulation Lab continues to use the server for bounded model scoring and temporary downloads, but its completed summary is copied into browser history. The demo UI does not rely on durable simulation/prediction rows for its recent-history list; active in-process work may be polled while the current server process is alive.

### Keep policy versions durable

Policy create/validate/activate/rollback continues to use PostgreSQL `policy_versions`, because the active policy must be consistent for model decisions and must survive a browser refresh. Policy audit history is outside the demo-local history surface and can be disabled or retained according to the existing deployment setting.

### Make scope visible in the UI

History sections must say “This browser only” or equivalent, provide a “Clear demo history” action, and explain that clearing browser data or changing browsers removes the history. The UI must never imply that browser-local records are shared production outcomes.

## Risks / Trade-offs

- [History can disappear] → Show the browser-only scope, provide empty-state guidance, and keep downloads explicit.
- [localStorage quota can be exceeded] → Bound item count and serialized size; treat writes as non-blocking warnings.
- [A user may mistake simulated outcomes for real feedback] → Label all local feedback and Simulation Lab records as synthetic/demo data.
- [Server restart can interrupt an active simulation] → Show unavailable/retry state and preserve only completed summaries that were already written to the browser.
- [Existing backend tests expect database logging] → Add a testable demo-local configuration path and retain durable mode for compatibility and production-like verification.
- [Changing persistence mode can create mixed history] → Version the storage keys and clear/migrate incompatible envelopes rather than guessing at their shape.

## Migration Plan

1. Add the local-history contract and storage utility behind an explicit demo-local configuration flag.
2. Add frontend capture/read/reset behavior for decision, feedback, and Simulation Lab summaries.
3. Update delayed-feedback and simulation recent-history UI to use the browser store in demo-local mode.
4. Keep existing PostgreSQL schema and durable mode available during rollout; do not drop tables or delete the policy volume.
5. Document that local history is per-browser and not an audit record.
6. Roll back by disabling demo-local mode and removing the local-history UI readers; existing durable endpoints and tables remain available.

## Open Questions

- Should demo-local mode be the default for the local Compose profile, or require an explicit `DEMO_LOCAL_HISTORY=true` setting?
- Should the Operations page hide “Simulate delayed feedback” and expose a local browser action instead, or keep the operation as a clearly labeled compatibility path?
- Should in-progress Simulation Lab metadata remain transient in ops memory, or should the browser submit a direct synchronous demo request for smaller scenarios?
