# operator-friendly-ux Specification

## Purpose
TBD - created by archiving change control-center-ux-redesign. Update Purpose after archive.
## Requirements
### Requirement: Natural-language presentation

The Control Center SHALL present business-facing labels and explanations for action names, reason codes, metric names, health states, and job states.

#### Scenario: Operator reviews a decision

- **WHEN** a decision result is displayed
- **THEN** the application SHALL show the recommended action and reasons in natural language
- **AND** SHALL explain uplift, expected value, and estimated customer value in context
- **AND** SHALL not require the operator to interpret raw enum names to understand the recommendation

#### Scenario: Operator reviews platform health

- **WHEN** service health or monitoring information is displayed
- **THEN** the application SHALL use readable labels and units
- **AND** SHALL explain what an abnormal state means and what action the operator can take

### Requirement: Progressive disclosure of technical details

The Control Center SHALL hide raw identifiers, raw logs, and implementation-specific payloads from the primary workflow while providing safe technical details through explicit disclosure when appropriate.

#### Scenario: Operator needs a reference

- **WHEN** an operator expands technical details for a decision or job
- **THEN** the application SHALL show the relevant reference, timestamp, or bounded diagnostic data
- **AND** SHALL provide a copyable reference where useful
- **AND** SHALL not expose secrets or unrestricted execution output

### Requirement: Usable decision input

The decision form SHALL group inputs by meaning, provide labels and helper text, validate fields accessibly, and distinguish required business inputs from advanced attributes.

#### Scenario: Operator enters a decision

- **WHEN** an operator completes the decision form
- **THEN** the application SHALL identify the user reference and estimated customer value in plain language
- **AND** SHALL group model attributes under an understandable advanced section
- **AND** SHALL show field-level validation before or alongside submission

#### Scenario: Decision form is invalid

- **WHEN** a required value is missing or outside the accepted range
- **THEN** the application SHALL identify the affected field
- **AND** SHALL explain how to correct it in plain language
- **AND** SHALL preserve other valid input values

### Requirement: Accessible and responsive interaction

The Control Center SHALL remain usable on supported desktop and narrow-screen layouts and SHALL communicate loading, success, warning, and error states with semantic text in addition to color.

#### Scenario: Operator uses a narrow screen

- **WHEN** the application viewport is narrow
- **THEN** navigation, forms, tables, and action controls SHALL remain reachable without horizontal clipping
- **AND** the primary task action SHALL remain visually prominent

#### Scenario: An operation completes

- **WHEN** a decision, refresh, or operational action completes
- **THEN** the application SHALL show a clear status message
- **AND** SHALL provide the next relevant action or result summary
