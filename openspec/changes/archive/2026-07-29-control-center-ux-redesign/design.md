## Context

The current Control Center is implemented as one dense page that combines service health, decisioning, monitoring, operations, and decision history. The existing API and policy engine already provide the core behavior, but the browser currently exposes too much implementation vocabulary and gives operators little guidance about which task to perform next.

The redesign must keep the Dockerized deployment model, preserve existing service volumes and specialist tools, and retain the server-side boundary around PostgreSQL, Prometheus, MLflow, and operations execution. It must also introduce an editable policy workflow without allowing an unvalidated or unaudited policy to become active.

## Goals / Non-Goals

### Goals

- Organize the Control Center into task-oriented routes: Overview, Decisions, Monitoring, Operations, and Policy.
- Make the primary information understandable to business and operations users through natural-language labels, explanations, and actionable empty/error states.
- Keep technical identifiers, raw logs, and service-specific details available through deliberate disclosure for authorized troubleshooting.
- Make decision inputs and outputs easier to complete, interpret, and verify.
- Provide a protected policy editor with validation, impact preview, version history, audit records, and rollback.
- Keep specialist links and existing operational safeguards intact.

### Non-Goals

- Changing the uplift model, treatment allocation algorithm, or decision-engine semantics.
- Automatically retraining or replacing the champion model from the new UI.
- Replacing Grafana or MLflow as specialist tools.
- Providing arbitrary shell, Docker, or database access from the browser.
- Introducing a production identity provider in this change; the existing configured admin authorization remains the boundary.

## Decisions

### 1. Use route-oriented task navigation

The web application will use a shared Control Center shell with a sidebar or compact navigation and separate routes for the five operator tasks. Each route will load only the data needed for that task and will preserve a consistent environment indicator, refresh control, and specialist-link area.

Route-oriented navigation is preferred over client-only tabs because it supports deep links, browser back/forward behavior, refresh isolation, and clearer ownership of loading/error states. The existing root route remains the Overview entrypoint.

### 2. Keep a server-side backend-for-frontend boundary

Next.js server-side routes or server actions will normalize responses from the API, operations service, Prometheus, MLflow, and policy store. Browser code will call only the web origin. Internal hostnames, credentials, raw database records, and unbounded execution output will not be passed to the browser by default.

### 3. Add a presentation mapping layer

The UI will map action names, reason codes, metric keys, health states, and job states to stable natural-language labels and explanations. Each task may expose a `Technical details` disclosure containing a safe reference, timestamp, or diagnostic value when it helps authorized troubleshooting. Raw IDs and logs will not be primary labels.

### 4. Treat feature values and customer value as context, not jargon

Decision input fields will use a feature metadata registry when one is available. Until the training data dictionary is formalized, `f0` through `f10` will be grouped under an advanced customer attributes section with a plain-language explanation and a link to the data dictionary. Customer value will be labeled as an estimated value used for ROI calculation, with helper text explaining that it is an input assumption rather than a directly observed fact.

### 5. Store policy versions in PostgreSQL with YAML migration fallback

Policy versions and policy-change audit records will be stored in additive PostgreSQL tables. The current YAML configuration will seed the initial active version during migration and remain a read-only fallback while the database is unavailable or not yet initialized. The decision engine will consume a validated active policy through the policy boundary; it will not read partially edited files.

Direct browser writes to YAML are rejected because they are unsafe across containers, difficult to roll back, and cannot provide reliable concurrent-update or audit behavior. The existing YAML file remains useful for bootstrap and local recovery, but database-backed versions are the source of truth after initialization.

### 6. Validate, preview, and authorize policy changes

The policy API will require the existing admin authorization mechanism for writes, validate both field-level and cross-field constraints, and expose a preview of the resulting policy impact before activation. Saves will use an expected active-version identifier to prevent lost updates. A successful activation creates an immutable version and audit record; rollback activates a prior validated version through the same protected path.

### 7. Use a small shared design system

The redesign will use reusable layout, status, metric, form, disclosure, and feedback components backed by shared CSS tokens. It will preserve the existing dark operational visual direction while improving contrast, spacing, typography, responsive behavior, keyboard focus, and semantic status messaging. No new UI framework is required unless the implementation shows a clear accessibility or maintenance benefit.

## Risks / Trade-offs

- A route-based refactor touches the current monolithic page. The migration should keep the existing root entrypoint and move one task at a time behind shared components.
- Database-backed policy storage adds migration and recovery work. Additive tables, an idempotent YAML seed, and a read-only fallback reduce deployment risk.
- Friendly labels can hide useful diagnostics. Technical details remain available through explicit disclosure and authorized specialist links.
- The feature metadata may initially be incomplete. The advanced-attributes fallback must be honest about the meaning and source of each value.
- Policy previews are estimates rather than guarantees of future uplift. The UI must label assumptions and retain the final policy version used for each decision where existing audit data supports it.
- Per-route polling can increase requests if uncontrolled. Refresh intervals will be bounded, paused when a route is hidden, and scoped to the active task.

## Migration Plan

1. Introduce shared layout, navigation, presentation mappings, and route-level loading/error states while keeping the current Overview behavior available.
2. Move Decisions, Monitoring, and Operations content into their task routes and preserve existing specialist links and operation endpoints.
3. Add additive policy-version and audit tables, seed the active version from YAML, and expose read/validate/preview/update/history/rollback contracts through the protected control plane.
4. Add the Policy route and confirmation workflow, then connect the decision engine to the validated active policy boundary.
5. Update tests, Compose configuration, documentation, and deployment checks; verify existing PostgreSQL, MLflow, Grafana, Prometheus, and dataset volumes remain untouched.

Rollback is achieved by reverting the web/control-plane deployment to the previous image and, for policy behavior, activating the last known-good immutable policy version. The YAML seed remains available for recovery during the migration window.

## Open Questions

- What business names and units should replace `f0` through `f10` once the training data dictionary is approved?
- Should the current admin token later be replaced or supplemented by SSO/RBAC? This is intentionally deferred from the implementation boundary.
- Which policy preview population and time window should be shown first when historical decision data is limited?
