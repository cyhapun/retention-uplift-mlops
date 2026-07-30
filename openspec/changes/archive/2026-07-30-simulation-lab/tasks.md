## 1. Prediction domain and contracts

- [x] 1.1 Define typed prediction request, status, model reference, policy mode, aggregate comparison, row-change summary, and result-download contracts.
- [x] 1.2 Add optional positive scenario customer-value validation and explicit model-only/policy-comparison modes.
- [x] 1.3 Implement vectorized baseline-versus-simulation prediction helpers using the champion model loader and paired synthetic row indexes.
- [x] 1.4 Implement policy comparison aggregates for action distribution, uplift, expected value, ROI, and changed recommendation count/share.
- [x] 1.5 Add unit tests for model-only mode, policy mode, paired rows, missing model output, invalid customer value, and summary calculations.

## 2. Prediction persistence and artifact lifecycle

- [x] 2.1 Add PostgreSQL `SimulationPredictionRun` metadata for simulation link, actor, request, status, model/policy references, timestamps, expiry, summary, and result artifact.
- [x] 2.2 Add atomic paired-result Parquet generation with synthetic row identifiers and bounded output size.
- [x] 2.3 Add on-demand CSV conversion/download using the existing simulation artifact root and retention policy.
- [x] 2.4 Extend startup reconciliation and expiry cleanup for queued/running prediction runs and partial result artifacts.
- [x] 2.5 Add lifecycle tests proving prediction runs never create decision/feedback logs and expired/partial result files are unavailable.

## 3. Operations control-plane API

- [x] 3.1 Add protected endpoints to start a prediction for a completed simulation, read status/summary, list recent prediction runs, and download paired results.
- [x] 3.2 Enforce model readiness, simulation ownership/status/expiry, policy mode, row/batch/output limits, and single-worker concurrency.
- [x] 3.3 Record prediction accepted, rejected, failed, expired, and downloaded actions with actor and related simulation identifiers.
- [x] 3.4 Capture the model URI/version and active policy version or configuration hash used by each run.
- [x] 3.5 Add backend tests for authorization, model-only mode, policy mode, status polling, concurrent requests, download formats, expiry, and safe failures.

## 4. Simulation Lab Control Center

- [x] 4.1 Add the `/simulation-lab` page and navigation item while preserving Operations for platform jobs and Monitoring for production signals.
- [x] 4.2 Add Next.js server-side proxy routes for simulation selection, prediction create/status/list, and Parquet/CSV result downloads.
- [x] 4.3 Move the existing drift simulator controls from Monitoring into Simulation Lab and keep a clearly labeled link from Monitoring.
- [x] 4.4 Add champion model readiness and optional illustrative customer-value controls with plain-language explanation of the assumption.
- [x] 4.5 Add prediction progress, model-only results, policy-comparison results, changed-recommendation summary, expiry, error, empty, and unavailable states.
- [x] 4.6 Add comparison cards and a result table for before/after uplift, action distribution, expected value/ROI when enabled, and result downloads.
- [x] 4.7 Add UI contract tests for navigation, isolation labels, value disclosure, progress, result states, and download links.

## 5. Deployment and documentation

- [x] 5.1 Add prediction batch size, output size, concurrency, and scenario-value settings to `docker-compose.yml` and `.env.example`.
- [x] 5.2 Add database initialization/migration coverage for prediction metadata and cleanup verification.
- [x] 5.3 Document the Simulation Lab workflow, model-only mode, policy comparison mode, customer-value assumption, and synthetic-data boundaries.
- [x] 5.4 Document why Simulation Lab results do not affect production decisions, metrics, feedback, retraining, or production drift reports.

## 6. Verification

- [x] 6.1 Run `ruff check src tests` and `ruff format src tests --check`.
- [x] 6.2 Run `pytest tests -q` including prediction isolation and authorization coverage.
- [x] 6.3 Run web UI tests and `npm run build`.
- [x] 6.4 Run `docker compose config` and build changed services.
- [x] 6.5 Verify the full Docker workflow: create drift, run model-only prediction, run policy comparison, inspect before/after results, download both formats, confirm production logs/metrics remain unchanged, and verify expiry cleanup.
