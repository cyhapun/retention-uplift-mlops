## Purpose

Provide a single Dockerized operator entrypoint for the RetentionOps uplift platform while keeping specialist tools available through deep links.

## MODIFIED Requirements

### Requirement: Monitoring and drift summary

The Control Center SHALL display selected Prometheus metrics and the latest production drift/retraining summary without requiring direct browser access to Prometheus or the report filesystem, SHALL explain the operational meaning of the values, and SHALL keep simulated-data results visually separate from production monitoring.

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

#### Scenario: No production drift report exists

- **WHEN** no production drift summary is available
- **THEN** the dashboard SHALL show that production monitoring data is unavailable
- **AND** SHALL not imply that the absence of a report means that the data is healthy

## ADDED Requirements

### Requirement: Guided drift simulator workspace

The Control Center SHALL provide a guided simulator workspace that lets an authorized operator select a preset or advanced feature transformations, submit a simulation, and view its progress without exposing raw filesystem paths or report payloads.

#### Scenario: Operator configures a simulation

- **WHEN** an operator opens the simulator
- **THEN** the UI SHALL show understandable presets, bounded row-count controls, and advanced feature controls
- **AND** SHALL explain that the result is synthetic test data rather than production evidence

#### Scenario: Simulation completes

- **WHEN** a submitted simulation completes successfully
- **THEN** the UI SHALL show affected features, before/after statistics, row count, severity, and expiry
- **AND** SHALL provide Parquet and CSV download actions
- **AND** SHALL keep raw report files hidden from the primary workflow

#### Scenario: Simulation fails or expires

- **WHEN** a simulation fails or its artifact expires
- **THEN** the UI SHALL show a plain-language status and recovery action
- **AND** SHALL not present a stale download link as available
