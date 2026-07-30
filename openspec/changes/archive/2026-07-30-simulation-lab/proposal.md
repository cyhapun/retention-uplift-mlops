## Why

The current drift simulator generates a synthetic dataset and shows feature-level before/after averages, but it stops before the most useful question: how does the champion model behave when those inputs change? Operators need one safe place to create a what-if scenario, run predictions against it, and compare recommendation outcomes without confusing synthetic results with production decisions.

## What Changes

- Rename the operator workflow to a dedicated Control Center tab named **Simulation Lab**, positioned alongside Operations.
- Extend a completed drift simulation with an explicit, bounded batch prediction step using the configured champion model.
- Compare baseline and simulated predictions, including action distribution, uplift/value aggregates, and the share of profiles whose recommendation changed.
- Show model readiness, simulation settings, prediction progress, comparison results, and downloadable prediction data in plain language.
- Make customer-value handling explicit: use a documented scenario value or show uplift-only results when value is not configured; never imply that simulated value is observed business value.
- Keep synthetic predictions out of production decision logs, Prometheus production counters, feedback records, retraining triggers, and the production drift card.
- Preserve the existing Parquet/CSV dataset downloads and temporary artifact retention.
- Keep the detailed production drift report as a separate explicit operation.

## Capabilities

### New Capabilities

- `simulation-lab`: End-to-end synthetic scenario creation, champion-model prediction, baseline comparison, result presentation, and controlled downloads.

### Modified Capabilities

- `operations-control`: Add an authenticated, allowlisted prediction job for simulation artifacts with lifecycle, resource, and audit controls.
- `unified-control-center`: Add the Simulation Lab task under Operations and distinguish simulation prediction results from production monitoring and decisions.

## Impact

- `src/ops` will gain a prediction worker/service that reads an approved simulation artifact, invokes the champion model, applies the active policy in simulation mode, and persists structured comparison results.
- `src/db` will store simulation prediction metadata and summaries without inserting synthetic rows into `decision_logs` or `feedback_logs`.
- The API/control plane will expose protected simulation prediction status, summary, and result downloads through opaque URLs.
- The Next.js Control Center will replace the current Monitoring simulator panel with a dedicated **Simulation Lab** page while keeping a link from Monitoring when useful.
- Docker configuration will add bounded prediction concurrency, batch size, output limits, and scenario customer-value settings while reusing the existing simulation named volume.
- Existing production serving, production metrics, drift reports, model training, model registration, and persistent volumes remain unchanged.
