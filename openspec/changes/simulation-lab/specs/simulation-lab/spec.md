## Purpose

Provide a safe what-if laboratory that runs the champion model on synthetic drift data and explains how predictions and policy recommendations change without creating production decisions.

## ADDED Requirements

### Requirement: Simulation Lab scenario and prediction workflow

The system SHALL provide an authenticated workflow that creates or selects a completed synthetic drift simulation, accepts an optional positive scenario customer value, and starts a bounded champion-model prediction run.

#### Scenario: Operator starts a model-only run

- **WHEN** an authorized operator selects a completed simulation without providing a customer value
- **THEN** the system SHALL run the champion model on paired baseline and simulated rows
- **AND** SHALL return treatment probability, control probability, and uplift comparisons
- **AND** SHALL mark policy action, expected value, and ROI comparisons as unavailable rather than inventing a value assumption

#### Scenario: Operator starts a policy comparison run

- **WHEN** an authorized operator provides a valid positive scenario customer value
- **THEN** the system SHALL apply the recorded active policy in simulation mode to both paired datasets
- **AND** SHALL calculate recommendation, treatment cost, expected value, and ROI comparisons
- **AND** SHALL label the value as an illustrative scenario assumption

#### Scenario: Simulation is not ready

- **WHEN** an operator selects a missing, failed, expired, or incomplete simulation
- **THEN** the system SHALL reject the prediction request
- **AND** SHALL explain that a completed non-expired simulation is required

### Requirement: Paired prediction comparison

The system SHALL compare predictions for the same baseline row slice and simulated row slice while preserving row pairing and SHALL provide aggregate and recommendation-change summaries.

#### Scenario: Predictions complete

- **WHEN** the champion model successfully scores both datasets
- **THEN** the result SHALL include row count, model reference, affected feature context, before/after average uplift, and recommendation-change count/share when policy comparison is enabled
- **AND** SHALL include action distributions when policy comparison is enabled
- **AND** SHALL persist a structured summary and a downloadable result artifact

#### Scenario: A recommendation changes

- **WHEN** the policy recommendation for a paired row differs between baseline and simulated inputs
- **THEN** the result SHALL count that row as changed
- **AND** SHALL not create a production decision log or feedback record for that row

### Requirement: Prediction result isolation

Simulation Lab predictions SHALL run outside the production decision and telemetry paths.

#### Scenario: Lab run executes

- **WHEN** a prediction run is accepted
- **THEN** the system SHALL not call the public decision endpoint for each row
- **AND** SHALL not write `decision_logs` or `feedback_logs`
- **AND** SHALL not increment production decision metrics
- **AND** SHALL not start training, registration, feedback generation, or production drift analysis

### Requirement: Plain-language Simulation Lab result

The Control Center SHALL display prediction progress and a result that clearly identifies synthetic data, model status, scenario assumptions, comparison metrics, creation time, and expiry.

#### Scenario: Operator views a completed result

- **WHEN** a prediction run completes
- **THEN** the UI SHALL show whether the result is model-only or includes policy comparison
- **AND** SHALL explain the number and share of recommendations changed when available
- **AND** SHALL provide Parquet and CSV result downloads without exposing internal paths or model identifiers in the primary view

#### Scenario: Prediction fails or expires

- **WHEN** the model cannot be loaded, the run fails, or its result artifact expires
- **THEN** the UI SHALL show a plain-language status and recovery action
- **AND** SHALL not present an unavailable download as active

### Requirement: Temporary prediction artifact lifecycle

Prediction result artifacts SHALL use the existing simulation named volume and retention policy, SHALL be finalized atomically, and SHALL be removed or marked unavailable after expiry or an unverified restart.

#### Scenario: Prediction artifact expires

- **WHEN** the configured result expiry is reached
- **THEN** the system SHALL remove the result artifact during cleanup
- **AND** SHALL return an expired/not-found response for subsequent downloads
- **AND** SHALL retain only the bounded metadata required by the audit policy
