## Purpose

Provide a controlled way to generate simulated drift data, understand the result, and download the dataset without modifying baseline data or producing raw reports by default.

## ADDED Requirements

### Requirement: Configurable drift simulation

The system SHALL accept a typed drift simulation request with a bounded row count, an optional preset, and an allowlisted set of per-feature transformations.

#### Scenario: Operator selects a preset

- **WHEN** an authorized operator submits a supported low, medium, or high drift preset
- **THEN** the system SHALL resolve it to validated feature transformations
- **AND** SHALL create a simulation run with a unique identifier
- **AND** SHALL not modify the reference or baseline dataset

#### Scenario: Operator uses advanced controls

- **WHEN** an authorized operator submits feature transformations using percentage scaling or absolute shifting
- **THEN** the system SHALL validate feature names, operation types, intensity bounds, duplicate definitions, and row limits
- **AND** SHALL reject unsupported or out-of-range values before creating a dataset

### Requirement: Safe simulation generation

The simulation service SHALL generate a new dataset from the configured baseline dataset and SHALL finalize it atomically under a dedicated simulation artifact root.

#### Scenario: Simulation succeeds

- **WHEN** the baseline dataset exists and the validated transformations complete
- **THEN** the system SHALL write a uniquely named Parquet artifact
- **AND** SHALL preserve the baseline dataset byte-for-byte
- **AND** SHALL persist a completed simulation status and summary

#### Scenario: Baseline data is unavailable

- **WHEN** the configured baseline dataset is missing or does not contain the required features
- **THEN** the system SHALL mark the simulation as failed
- **AND** SHALL return an actionable error
- **AND** SHALL not create a downloadable artifact

### Requirement: Plain-language simulation summary

The system SHALL provide a structured summary for each completed simulation without requiring the operator to open an HTML or JSON drift report.

#### Scenario: Operator views a completed simulation

- **WHEN** a simulation is completed
- **THEN** the system SHALL show row count, affected feature count, drift severity, creation time, and expiry time
- **AND** SHALL show before/after statistics and the applied transformation for each affected feature
- **AND** SHALL label the result as simulated data

### Requirement: Temporary artifact download

The system SHALL retain generated artifacts only until their configured expiry and SHALL provide authorized Parquet and CSV downloads through opaque application URLs.

#### Scenario: Operator downloads a simulation

- **WHEN** an authorized operator requests a non-expired simulation in a supported format
- **THEN** the system SHALL stream the dataset with a safe filename and correct content type
- **AND** SHALL not expose the host filesystem path

#### Scenario: Simulation has expired

- **WHEN** an operator requests a simulation after its artifact expiry
- **THEN** the system SHALL return an expired/not-found response
- **AND** SHALL not recreate the artifact implicitly

### Requirement: Simulation does not trigger production analysis

The system SHALL keep simulation generation separate from the detailed production drift-report workflow and SHALL not automatically start retraining.

#### Scenario: Simulation is created

- **WHEN** a simulation completes
- **THEN** the system SHALL not write a production drift report by default
- **AND** SHALL not start model training or model registration
- **AND** SHALL allow an explicit later analysis workflow to use the generated artifact when configured
