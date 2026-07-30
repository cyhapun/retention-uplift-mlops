## Context

The completed `drift-simulator-ux` change creates a temporary synthetic Parquet dataset and a feature-level summary. It intentionally does not send the data through the model, because the existing Decision API logs every request as a production decision and increments production Prometheus counters. The next workflow must answer the model-behavior question without polluting production telemetry or decision history.

The Control Center currently has a Monitoring page with the simulator panel and an Operations page for allowlisted jobs. The requested user experience is a dedicated top-level **Simulation Lab** tab that combines scenario configuration, isolated prediction, and before/after comparison. Monitoring remains the place for real production health and drift signals.

## Goals / Non-Goals

### Goals

- Run the champion model on both the selected baseline rows and the generated drift rows.
- Compare model outputs and policy recommendations in a single synthetic experiment.
- Make customer value assumptions visible and optional rather than presenting them as observed business truth.
- Persist prediction job metadata and summaries in PostgreSQL and temporary result files in the existing simulation volume.
- Keep prediction jobs authenticated, bounded, auditable, restart-safe, and isolated from production logs/metrics/feedback.
- Provide a dedicated Simulation Lab page with progress, comparison cards, explanations, and downloads.

### Non-Goals

- Calling the public `/decide-action` endpoint for each row.
- Writing simulated rows into `decision_logs` or `feedback_logs`.
- Incrementing production Prometheus counters or changing the production drift card.
- Retraining, registering, or replacing the champion model.
- Treating simulated expected value, ROI, or recommendation changes as observed business outcomes.
- Building a general batch-serving or customer-segmentation platform.

## Decisions

### 1. Add a dedicated isolated prediction worker

The ops service will load the configured champion model through the same model-loader contract used by serving, run vectorized predictions on baseline and drifted DataFrames, and apply the active policy in memory. It will not call the public Decision API because that endpoint logs decisions and records production metrics by design.

The worker will persist the model URI/version and policy snapshot reference used for the run. A single bounded worker avoids duplicate model loads and keeps resource use predictable. A future batch-serving service can replace the worker behind the same API contract.

### 2. Use an optional scenario customer value

The prediction request will accept an optional positive `customer_value`. When present, the worker will calculate policy action, treatment cost, expected value, and ROI for both datasets. When absent, the result will contain probabilities and uplift only, with action/value comparison marked unavailable. The UI will label a provided value as an illustrative scenario assumption.

This prevents the lab from hiding the same customer-value assumption problem as the interactive decision form while still allowing a useful model-only comparison.

### 3. Compare paired baseline and drift outputs

The worker will use the same baseline row slice as the generated simulation, preserving row order and a synthetic row index. It will calculate aggregate before/after metrics and the number/share of rows whose recommendation changed. Per-row results will contain only synthetic row identifiers, model outputs, and optional policy outputs; they will not contain production user IDs.

### 4. Persist prediction runs separately from simulation generation

Add a `SimulationPredictionRun` record linked to a simulation. It will store request settings, status, actor, model/policy references, timestamps, expiry, summary JSON, and a result artifact filename. This allows a simulation dataset to be analyzed more than once with a different customer-value assumption without rewriting the source simulation artifact.

The result artifact will be one canonical Parquet file containing paired baseline/drift columns. CSV will be converted on demand using the existing bounded download path. Both files share the simulation retention policy and named volume.

### 5. Create a dedicated Simulation Lab page

Add `/simulation-lab` to the Control Center navigation. The page will let the operator create a scenario or select a recent completed simulation, enter an optional illustrative customer value, start prediction, and view progress/result/error/expiry states. Monitoring will remove the full simulator form and retain only production drift plus a link to Simulation Lab.

### 6. Keep the boundary explicit in labels and APIs

Every prediction response and result card will be labeled synthetic/simulated. Download URLs will be opaque application routes. The browser will never receive internal model paths, filesystem paths, database credentials, or admin tokens.

## Risks / Trade-offs

- [Risk] Loading the champion model in ops duplicates model memory → use one worker, reject concurrent prediction runs, and expose configured row/batch limits.
- [Risk] A user interprets simulated ROI as real revenue → require an explicit label for scenario customer value and show model-only mode when omitted.
- [Risk] Large result files consume the temporary volume → enforce row, output-size, batch-size, and TTL limits and reuse cleanup/restart reconciliation.
- [Risk] Policy changes during a run make comparisons hard to reproduce → snapshot the active policy or record a stable policy version/config hash with the prediction run.
- [Risk] Model unavailable in MLflow → fail with a plain-language status and preserve the source simulation artifact until its normal expiry.
- [Risk] Existing UI links or tests assume five navigation tabs → update navigation contracts and preserve the Operations page for platform jobs.

## Migration Plan

1. Add prediction contracts, model-only batch predictor, policy comparison helpers, and unit tests.
2. Add prediction metadata/result artifact tables and extend cleanup/restart handling.
3. Add protected ops endpoints and server-side Next.js proxy routes.
4. Move the simulator UI to `/simulation-lab`, add prediction controls/results, and link to it from Monitoring.
5. Update Compose/environment limits and operator documentation.
6. Run Python/web/Docker checks and verify that production decision logs, metrics, and drift summaries remain unchanged during a lab run.

Rollback is additive: hide the Simulation Lab route and disable prediction endpoints. Existing drift dataset generation, production decisions, operations, and persistent volumes remain usable.

## Open Questions

- Should the first version support only the currently registered champion alias, or allow selecting another registered model/version for comparison?
- Should the lab always require a customer value for policy recommendations, or is model-only mode sufficient for the first release?
- Should the result include a small chart in the first version, or are comparison cards and downloadable data enough initially?
