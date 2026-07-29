## Why

The current RetentionOps Control Center presents health, decisioning, monitoring, operations, and history in one dense page. Technical identifiers, raw operation names, and model terminology make the interface difficult for non-technical operators to understand and use confidently. The policy engine is also configuration-driven but has no safe, discoverable UI for reviewing or changing its thresholds.

This change reorganizes the Control Center around operator tasks, translates technical output into business language, and adds a protected policy management workflow with validation and auditability.

## What Changes

- Replace the single long dashboard with task-oriented navigation for Overview, Decisions, Monitoring, Operations, and Policy.
- Redesign the visual hierarchy, spacing, typography, status indicators, responsive behavior, loading states, and empty/error states.
- Replace raw enum names, metric keys, reason codes, IDs, and log output with natural-language labels and progressive disclosure of technical details.
- Improve the decision workflow with clearer customer context, understandable result explanations, feature metadata, and accessible validation feedback.
- Add a Policy tab that displays action costs, uplift thresholds, expected-value thresholds, priorities, and global limits in editable business language.
- Protect policy changes with admin authorization, validation, confirmation, audit records, and a rollback/version history strategy.
- Keep specialist links to MLflow, Grafana, Prometheus, and API documentation available from the relevant task areas.
- Preserve existing decision, monitoring, operation, and volume behavior while changing the operator-facing presentation.

## Capabilities

### New Capabilities

- `control-center-navigation`: Task-oriented tabs/routes and focused data loading for the Control Center.
- `policy-management`: Review, validate, edit, audit, and safely apply decision policy configuration.
- `operator-friendly-ux`: Natural-language presentation, technical-detail disclosure, accessible states, and responsive interaction patterns.

### Modified Capabilities

- `unified-control-center`: Add task-oriented navigation, clearer business-language summaries, and progressive disclosure of technical data.
- `operations-control`: Extend the protected operations boundary to cover policy changes, validation, audit history, and rollback behavior.

## Impact

- `web/app/page.tsx` and `web/app/globals.css` will be refactored into a route/tab-oriented UI with reusable presentation components.
- New Next.js server-side routes will expose policy reads, validation, updates, and history without exposing internal service credentials.
- `src/ops` will gain normalized policy contracts and protected policy management endpoints.
- `src/policy` will gain a validated persistence/update boundary while preserving the existing policy engine semantics.
- PostgreSQL may receive additive policy version and audit tables, depending on the selected persistence strategy.
- Existing `docker-compose.yml`, environment variables, tests, documentation, and specialist links will be updated as needed.
