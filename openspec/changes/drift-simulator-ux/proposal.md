## Why

The current Drift Simulator always changes the same three features with hard-coded transformations and writes one fixed `test_drifted.parquet` file. It does not let an operator choose which attributes drift or how strongly, and the next “Refresh drift report” operation still analyzes the baseline dataset unless a separate command is run manually. This makes the demo difficult to understand and couples simulation to raw report files.

The simulator should become an intentional, reversible UI workflow: the operator configures a bounded scenario, sees a plain-language result summary, and downloads the generated dataset only when needed. Detailed drift analysis remains a separate explicit action for operators who need it.

## What Changes

- Add a parameterized Drift Simulator workflow with safe presets and advanced per-feature controls.
- Validate feature names, transformation types, intensity limits, row limits, and output formats at the server boundary.
- Generate a unique simulation artifact instead of overwriting `data/processed/test_drifted.parquet`.
- Calculate and return a concise simulation summary with affected features, before/after statistics, row count, drift level, and creation status.
- Keep generated Parquet/CSV files in a dedicated temporary Docker volume with configurable expiry; do not store them in the source tree or PostgreSQL.
- Add download endpoints for generated datasets and expose download actions from the Control Center.
- Show simulation progress, results, errors, and the distinction between simulated data and production drift monitoring in the UI.
- Keep the existing detailed drift report as an explicit optional analysis workflow rather than an automatic side effect of simulation.
- Preserve the allowlisted operations boundary, admin authorization, existing persistent volumes, and the rule that drift never automatically starts model training.

## Capabilities

### New Capabilities

- `drift-simulation`: Controlled generation, summary, temporary storage, expiry, and download of simulated drift datasets.

### Modified Capabilities

- `operations-control`: Extend the protected control plane with validated simulation parameters, structured results, artifact lifecycle, and download authorization.
- `unified-control-center`: Add an operator-facing simulator workflow and clearly separate simulation results from production drift signals.

## Impact

- `src/monitoring/simulate_drift.py` will accept validated transformation specifications and return structured summary data.
- `src/ops` and PostgreSQL will gain simulation metadata, result, authorization, and cleanup boundaries; generated datasets will use a dedicated named volume.
- New Next.js server-side routes will create simulations, poll status, and stream approved Parquet/CSV downloads without exposing internal paths.
- `web/app/components/task-pages.tsx` and shared UI components will gain a guided simulator panel and result state.
- `docker-compose.yml`, environment documentation, and operator documentation will define the simulation volume and retention period.
- Existing `reports/drift/` detailed report behavior remains available for explicit analysis and is not removed by this change.
