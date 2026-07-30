## Why

The current demo persists decisions, simulated feedback, operations, and Simulation Lab metadata in PostgreSQL even though these records are not required for the local demonstration. This adds database noise and makes the prototype look more like a production audit system than an interactive demo. The demo should keep only policy configuration durable while allowing the current browser to revisit its own recent results.

## What Changes

- Add a browser-local history for demo decisions, simulated feedback, and Simulation Lab summaries using `localStorage`.
- Keep `policy_versions` as the only durable PostgreSQL business-history store for the demo workflow.
- Stop requiring PostgreSQL writes for demo decision results, delayed-feedback simulation, operation history, and Simulation Lab run history.
- Keep generated large artifacts temporary and downloadable; do not place Parquet/CSV payloads in `localStorage`.
- Add clear empty, unavailable, quota, and reset-history states so users understand that history belongs only to the current browser profile.
- Preserve model inference, policy evaluation, Prometheus request metrics, and protected server-side integration boundaries.
- Mark the behavior as demo-only and explicitly distinguish browser-local history from production audit, shared history, and durable analytics.

## Capabilities

### New Capabilities

- `demo-local-history`: Store and restore bounded demo history in the current browser without exposing sensitive data or requiring durable decision/feedback/simulation records.

### Modified Capabilities

- `unified-control-center`: Change the dashboard and decision playground to show browser-local history and explain its scope instead of presenting PostgreSQL-backed demo history.
- `operations-control`: Allow demo feedback and simulation history to be transient or browser-owned while retaining protected policy management and model/service controls.
- `simulation-lab`: Keep prediction execution and temporary downloads available without persisting simulation and prediction metadata as durable PostgreSQL history.

## Impact

- Frontend: add a typed local-history store, hydration-safe hooks, bounded retention, reset controls, and history displays for Decisions, feedback, and Simulation Lab.
- Backend: make demo persistence configurable or stateless for decision/feedback/simulation flows, while retaining policy version storage and existing model/policy APIs.
- PostgreSQL: `policy_versions` remains durable; other demo tables may remain in the schema for compatibility but are not written in local-history mode.
- Browser storage: use `localStorage` for compact summaries only; keep large result files in temporary server/volume storage or direct downloads.
- Tests and documentation: cover reload persistence, per-browser isolation, quota/corrupt-data recovery, reset behavior, and the distinction from production audit.
