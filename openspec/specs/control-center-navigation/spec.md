# control-center-navigation Specification

## Purpose
TBD - created by archiving change control-center-ux-redesign. Update Purpose after archive.
## Requirements
### Requirement: Task-oriented Control Center navigation

The Control Center SHALL provide distinct navigation destinations for Overview, Decisions, Monitoring, Operations, and Policy within one web application shell.

#### Scenario: Operator changes task

- **WHEN** an operator selects a navigation destination
- **THEN** the application SHALL navigate to the selected task view
- **AND** SHALL keep the environment indicator, refresh control, and primary navigation available
- **AND** SHALL show the selected destination as active

#### Scenario: Operator opens a deep link

- **WHEN** an operator opens a supported task URL directly or refreshes it
- **THEN** the application SHALL render that task view without requiring a visit to Overview first
- **AND** SHALL preserve the active navigation state

### Requirement: Focused task data loading

Each task view SHALL request only the data needed for that task through the server-side web boundary and SHALL expose a bounded refresh state.

#### Scenario: Task data is loading

- **WHEN** a task view is waiting for its data
- **THEN** the view SHALL show a meaningful loading state in the affected region
- **AND** SHALL keep navigation usable

#### Scenario: Task data fails

- **WHEN** a task data request fails or times out
- **THEN** the view SHALL show a plain-language recovery message
- **AND** SHALL provide a retry action when retrying is safe
- **AND** SHALL not expose internal credentials or unbounded service output

### Requirement: Specialist links remain discoverable

The Control Center SHALL expose configured links to Grafana, MLflow, Prometheus, and API documentation from the task areas where they are relevant.

#### Scenario: Operator needs specialist investigation

- **WHEN** an operator views Monitoring, Decisions, or Overview
- **THEN** the application SHALL provide the relevant configured specialist link
- **AND** SHALL describe what the destination is useful for in natural language
