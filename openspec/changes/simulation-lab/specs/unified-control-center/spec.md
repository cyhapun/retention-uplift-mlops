## MODIFIED Requirements

### Requirement: Unified dashboard entrypoint

The system SHALL provide a Dockerized Next.js Control Center as the primary operator-facing entrypoint for the RetentionOps stack, with task-oriented navigation for Overview, Decisions, Monitoring, Simulation Lab, Operations, and Policy.

#### Scenario: Operator opens the control center

- **WHEN** an operator navigates to the configured web entrypoint
- **THEN** the system SHALL render the Overview task without requiring the operator to open separate service UIs for the core overview
- **AND** the dashboard SHALL identify the current environment and refresh state
- **AND** the operator SHALL be able to reach Simulation Lab and the other task views from the same shell

### Requirement: Monitoring and drift summary

The Control Center SHALL display selected Prometheus metrics and the latest production drift/retraining summary without requiring direct browser access to Prometheus or the report filesystem, SHALL explain the operational meaning of the values, and SHALL keep Simulation Lab results separate from production monitoring.

#### Scenario: Dashboard refreshes metrics

- **WHEN** the configured refresh interval elapses
- **THEN** the dashboard SHALL request bounded metric data through the server-side integration
- **AND** SHALL render request rate, latency, error rate, action distribution, average uplift, and expected value when data is available
- **AND** SHALL show metric names and units in readable language

#### Scenario: Latest production drift report exists

- **WHEN** a valid production drift summary is available
- **THEN** the dashboard SHALL show drifted feature count, drift share, retraining recommendation, and retraining reasons
- **AND** SHALL explain that production drift is a change in input-data distribution compared with the reference data
- **AND** SHALL provide a link to the detailed report when configured

#### Scenario: Simulation Lab result exists

- **WHEN** a synthetic prediction result is available
- **THEN** the Monitoring page SHALL not merge it into production drift or production decision metrics
- **AND** SHALL provide at most a clearly labeled link to open the Simulation Lab result

## ADDED Requirements

### Requirement: Simulation Lab workspace

The Control Center SHALL provide a dedicated top-level **Simulation Lab** tab for configuring synthetic scenarios, running isolated champion-model predictions, and reviewing paired before/after results.

#### Scenario: Operator opens Simulation Lab

- **WHEN** an operator opens the Simulation Lab tab
- **THEN** the UI SHALL show recent completed simulations, scenario controls, model readiness, and an explanation that all results are synthetic
- **AND** SHALL not expose filesystem paths, database credentials, admin tokens, or raw production logs

#### Scenario: Operator runs a prediction comparison

- **WHEN** an authorized operator selects a completed simulation and starts a prediction comparison
- **THEN** the UI SHALL show queued/running progress
- **AND** SHALL show baseline versus simulated uplift, policy outcomes when a scenario customer value is provided, changed recommendation count/share, result expiry, and download actions when complete

#### Scenario: Simulation Lab is unavailable

- **WHEN** the champion model is unavailable, authorization is not configured, or a prediction fails
- **THEN** the UI SHALL show a plain-language explanation and recovery action
- **AND** SHALL keep production Monitoring and read-only dashboard areas available when possible
