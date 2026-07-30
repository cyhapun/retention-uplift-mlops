## 1. Simulation domain and validation

- [x] 1.1 Define typed simulation request, transformation, preset, status, summary, and download contracts in `src/monitoring`/`src/ops`.
- [x] 1.2 Define low, medium, and high drift presets and bounded defaults for row count, feature intensity, output size, and retention period.
- [x] 1.3 Refactor `src/monitoring/simulate_drift.py` to apply allowlisted percentage-scale and absolute-shift transformations without overwriting the baseline dataset.
- [x] 1.4 Add pure before/after statistics and drift-severity calculation that does not create Evidently HTML/JSON reports.
- [x] 1.5 Add validation tests for presets, unknown features, duplicate transformations, unsupported operations, intensity limits, and row limits.

## 2. Persistence and artifact lifecycle

- [x] 2.1 Add PostgreSQL models and initialization for simulation metadata, request parameters, structured summary, status, actor, timestamps, and expiry.
- [x] 2.2 Add a configurable simulation artifact root and atomic temporary-to-final file workflow for Parquet output.
- [x] 2.3 Add configurable retention cleanup that removes only expired simulation artifacts and reconciles incomplete simulations after an ops restart.
- [x] 2.4 Add a Docker named volume for simulation artifacts and mount it only where generation and download require access.
- [x] 2.5 Add tests proving baseline/reference datasets remain unchanged and expired or partial artifacts are not downloadable.

## 3. Operations control-plane API

- [x] 3.1 Add protected endpoints to create a simulation, read status/summary, and list the operator's recent simulations without exposing host paths.
- [x] 3.2 Enforce admin authorization, request validation, concurrency limits, resource limits, and safe error messages for simulation creation.
- [x] 3.3 Add Parquet download streaming with a safe filename and content type after authorization and expiry checks.
- [x] 3.4 Add on-demand CSV conversion/download with bounded output and cleanup of conversion temporary files.
- [x] 3.5 Add audit records and structured job/result status for accepted, rejected, failed, expired, and downloaded simulation actions.
- [x] 3.6 Add backend tests for successful creation, status polling, authorization, concurrent requests, download formats, expiry, cleanup, and restart recovery.

## 4. Control Center experience

- [x] 4.1 Add Next.js server-side proxy routes for simulation create/status/list/download while keeping internal URLs, tokens, and filesystem paths server-side.
- [x] 4.2 Add a guided Drift Simulator panel in Monitoring or Operations with presets, row-count control, advanced feature transformations, and plain-language help.
- [x] 4.3 Add progress, success, failure, expired, and empty states that clearly distinguish simulated data from production drift monitoring.
- [x] 4.4 Add result cards showing affected features, before/after statistics, row count, severity, creation time, expiry, and Parquet/CSV download actions.
- [x] 4.5 Remove the fixed `test_drifted.parquet` simulation button behavior while keeping the explicit production drift-report action available.
- [x] 4.6 Add UI contract tests for validation feedback, simulation progress, result summary, expiry state, download links, and raw-report disclosure.

## 5. Deployment and documentation

- [x] 5.1 Update `docker-compose.yml` and `.env.example` with the simulation named volume, artifact root, row/file limits, and retention settings without changing existing persistent volumes.
- [x] 5.2 Add a migration/initialization command for simulation metadata and cleanup verification.
- [x] 5.3 Document the simulator workflow, preset meanings, advanced controls, temporary storage behavior, download formats, and the difference from production drift analysis.
- [x] 5.4 Document how to explicitly analyze a generated simulation with the existing detailed drift-report workflow when needed.

## 6. Verification

- [x] 6.1 Run `ruff check src tests` and `ruff format src tests --check`.
- [x] 6.2 Run `pytest tests -q` including simulation lifecycle and authorization coverage.
- [x] 6.3 Run web UI tests and `npm run build`.
- [x] 6.4 Run `docker compose config` and build changed services.
- [x] 6.5 Verify simulation creation, summary display, Parquet/CSV downloads, expiry cleanup, production drift-report separation, named-volume persistence, and service health in Docker Compose.
