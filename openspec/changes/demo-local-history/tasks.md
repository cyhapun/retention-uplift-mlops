## 1. Local history contract

- [x] 1.1 Define versioned TypeScript types for decision, feedback, simulation, prediction, and local-history envelopes.
- [x] 1.2 Implement a client-only `localStorage` store with hydration-safe reads, bounded item counts, serialized-size limits, and best-effort writes.
- [x] 1.3 Add per-collection reset, whole-demo reset, malformed-envelope recovery, unsupported-version recovery, and quota-warning helpers.
- [x] 1.4 Add unit tests for reload restoration, browser-only scope, bounded retention, corrupt data, quota failure, and reset behavior.

## 2. Demo-local backend boundary

- [x] 2.1 Add an explicit `DEMO_LOCAL_HISTORY` configuration flag with safe local-demo defaults and production-like durable mode preserved.
- [x] 2.2 Make decision logging optional for demo-local mode while keeping model inference, policy evaluation, response contracts, and Prometheus request metrics unchanged.
- [x] 2.3 Make operation status and audit persistence optional for demo-local mode while retaining allowlisted commands, authorization, concurrency, and failure handling.
- [x] 2.4 Make simulation and prediction metadata persistence optional for demo-local mode while keeping bounded inference, temporary artifacts, polling, expiry, and protected downloads available.
- [x] 2.5 Keep policy version creation, activation, rollback, and active-policy reads durable in PostgreSQL; add tests proving demo actions do not write the other history tables.

## 3. Browser-owned decision and feedback history

- [x] 3.1 Save sanitized successful decision summaries to browser-local history after the decision API responds.
- [x] 3.2 Add a Decisions history section with readable entries, empty state, browser-only disclosure, and clear-history controls.
- [x] 3.3 Replace demo delayed-feedback database lookup with a browser-local feedback simulation over saved decision summaries.
- [x] 3.4 Add feedback history and outcome summary presentation without storing raw features or credentials locally.
- [x] 3.5 Add frontend tests for decision capture, feedback simulation, reload behavior, reset behavior, and disabled/empty states.

## 4. Browser-owned Simulation Lab history

- [x] 4.1 Save completed synthetic scenario summaries and prediction comparison summaries to browser-local history.
- [x] 4.2 Update Simulation Lab recent-history loading to use local history in demo-local mode while preserving active server polling.
- [x] 4.3 Show expired-download and server-restart states without deleting the browser-local summary.
- [x] 4.4 Add a clear Simulation Lab history action and explain that result files are temporary and browser history is local.
- [x] 4.5 Add UI contract tests for Simulation Lab local history, disclosure, expiry, reset, and download boundaries.

## 5. Deployment and documentation

- [x] 5.1 Add demo-local persistence settings to `.env.example`, Docker Compose, and the Control Center runtime configuration.
- [x] 5.2 Ensure PostgreSQL schema initialization does not imply that demo history tables are actively written in local mode.
- [x] 5.3 Document localStorage limits, per-browser behavior, synthetic feedback, policy persistence, and the difference from production audit.
- [x] 5.4 Add a visible demo-mode indicator and a safe recovery path when local storage is unavailable.

## 6. Verification

- [x] 6.1 Run `ruff check src tests` and `ruff format src tests --check`.
- [x] 6.2 Run the full Python test suite including database-write isolation and durable-policy coverage.
- [x] 6.3 Run web UI tests and `npm run build`.
- [x] 6.4 Run `docker compose config`, build changed services, and verify service health.
- [ ] 6.5 Verify decision, feedback, and Simulation Lab reload/reset behavior in a browser while confirming only `policy_versions` changes in PostgreSQL.
