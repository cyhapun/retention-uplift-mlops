## 1. Control Center foundation

- [x] 1.1 Define shared UI tokens, typography, spacing, status colors, focus states, and responsive breakpoints in `web/app/globals.css`.
- [x] 1.2 Split the monolithic Control Center page into reusable shell, navigation, card, status, metric, form, disclosure, and feedback components.
- [x] 1.3 Add route-oriented task pages for Overview, Decisions, Monitoring, Operations, and Policy while preserving the root Overview entrypoint.
- [x] 1.4 Add route-level loading, empty, timeout, and retry states that keep the shared navigation usable.
- [x] 1.5 Add automated UI tests for active navigation, direct task URLs, narrow-screen layout, keyboard focus, and semantic status messages.

## 2. Server-side data and presentation contracts

- [x] 2.1 Inventory the existing dashboard, API, operations, Prometheus, MLflow, and drift response shapes and define stable web-facing TypeScript contracts.
- [x] 2.2 Add server-side adapters for task-specific data loading so browser code calls only the Next.js origin.
- [x] 2.3 Add shared presentation mappings for action names, reason codes, metric names, health states, job states, units, and recovery guidance.
- [x] 2.4 Add bounded refresh behavior scoped to the active task and prevent internal credentials, unrestricted logs, and sensitive payloads from reaching the browser.
- [x] 2.5 Add feature metadata support with a documented advanced-attributes fallback for `f0` through `f10` and label customer value as an estimate used for ROI.

## 3. Operator workflow redesign

- [x] 3.1 Rebuild the Overview route around platform health, champion model readiness, recent decisions, and specialist links using the shared presentation layer.
- [x] 3.2 Rebuild the Decisions route with grouped business inputs, accessible validation, advanced-attribute disclosure, understandable result explanations, and secondary technical references.
- [x] 3.3 Rebuild the Monitoring route with readable metric units, drift explanation, retraining guidance, bounded refresh, and Grafana/Prometheus links.
- [x] 3.4 Rebuild the Operations route with natural-language operation labels, concise job summaries, safe failure messages, bounded technical details, and existing allowlisted controls.
- [x] 3.5 Verify specialist links to MLflow, Grafana, Prometheus, and API documentation remain configured and reachable from relevant task views.

## 4. Policy persistence and control-plane API

- [x] 4.1 Define additive PostgreSQL schema and migrations for immutable policy versions, active-version state, and policy-change audit records.
- [x] 4.2 Implement an idempotent seed from `src/policy/policy_config.yaml` and a read-only YAML fallback for an uninitialized or unavailable policy store.
- [x] 4.3 Add validated policy domain models and repository/service methods for active policy reads, version creation, activation, history, and rollback.
- [x] 4.4 Add protected control-plane endpoints for policy read, validation, impact preview, activation, history, and rollback using the configured admin authorization.
- [x] 4.5 Enforce field-level and cross-field policy validation, expected active-version checks, explicit confirmation, and non-mutating behavior on rejected requests.
- [x] 4.6 Add audit records for successful and rejected policy changes without storing secrets or full credentials.
- [x] 4.7 Update the decision-engine policy boundary so each decision uses one complete validated active policy version and preserves existing action-selection semantics.
- [x] 4.8 Add backend tests for policy validation, YAML seeding/fallback, authorization, concurrent updates, preview behavior, activation, rollback, and audit history.

## 5. Policy user experience

- [x] 5.1 Build the Policy route showing active version, action costs, uplift/value thresholds, priorities, global limits, units, and editability state in business language.
- [x] 5.2 Add editable policy forms with field-level validation, unsaved-change protection, accessible confirmation, and clear activation feedback.
- [x] 5.3 Add policy impact preview UI showing population, time window, estimated action-distribution and value changes, plus an honest unavailable-data state.
- [x] 5.4 Add policy history and rollback UI with protected actions, version comparison, confirmation, and visible audit outcomes.
- [x] 5.5 Add UI tests covering read-only mode, invalid edits, preview, activation, rollback, authorization errors, and concurrent-update feedback.

## 6. Deployment, documentation, and verification

- [x] 6.1 Update Docker Compose and environment documentation for policy persistence, migrations, admin authorization, and any new web/control-plane routes without changing existing data volumes destructively.
- [x] 6.2 Document the operator workflows, policy field meanings, customer-value assumption, drift explanation, technical-details disclosure, and rollback procedure.
- [x] 6.3 Run `ruff check src tests` and `ruff format src tests --check`.
- [x] 6.4 Run `pytest tests -q` including the new policy and web-boundary coverage.
- [x] 6.5 Run `docker compose config`, build the changed services, and verify health endpoints, named volumes, specialist links, and task navigation in the Dockerized stack.
