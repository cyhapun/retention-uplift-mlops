## Purpose

Provide a safe, understandable, and auditable workflow for reviewing and changing the uplift decision policy from the Control Center.

## ADDED Requirements

### Requirement: Policy overview

The Policy view SHALL display the active policy version, action rules, costs, minimum uplift thresholds, minimum expected-value thresholds, priorities, and global limits in business-readable terms.

#### Scenario: Operator opens Policy

- **WHEN** an operator opens the Policy view
- **THEN** the application SHALL show the active policy and when it became active
- **AND** SHALL explain the meaning and units of each editable value
- **AND** SHALL indicate whether the policy is editable for the current operator

### Requirement: Validated policy editing

The policy management boundary SHALL validate every proposed policy before it can become active, including field types, non-negative costs, valid priorities, threshold ranges, and cross-field consistency.

#### Scenario: Proposed policy is valid

- **WHEN** an authorized operator submits a policy that passes all validation rules
- **THEN** the system SHALL create a new immutable policy version
- **AND** SHALL require explicit confirmation before activation
- **AND** SHALL retain the previous active version for rollback

#### Scenario: Proposed policy is invalid

- **WHEN** a proposed policy fails field-level or cross-field validation
- **THEN** the system SHALL reject activation
- **AND** SHALL return actionable validation messages tied to the affected fields
- **AND** SHALL leave the active policy unchanged

### Requirement: Policy impact preview

The Policy view SHALL provide an impact preview for a valid proposed policy before activation when the required historical data is available.

#### Scenario: Preview is available

- **WHEN** an operator requests a preview for a valid proposed policy
- **THEN** the system SHALL show the evaluation period and population used
- **AND** SHALL summarize expected changes to action distribution, estimated cost, uplift, and expected value
- **AND** SHALL label the result as an estimate

#### Scenario: Preview data is unavailable

- **WHEN** historical data is insufficient for a preview
- **THEN** the application SHALL explain why the estimate is unavailable
- **AND** SHALL not block viewing the current policy
- **AND** SHALL require an explicit confirmation before a policy can still be activated

### Requirement: Protected policy changes

Policy creation, activation, and rollback SHALL require the configured admin authorization mechanism and SHALL remain disabled when that authorization is not configured.

#### Scenario: Unauthorized policy update is requested

- **WHEN** a request to create, activate, or roll back a policy lacks valid admin authorization
- **THEN** the system SHALL return an authorization error
- **AND** SHALL not change the active policy
- **AND** SHALL not reveal protected policy history beyond the minimum public status

### Requirement: Policy history and rollback

The system SHALL keep immutable policy versions and an audit record for successful and rejected policy changes, including actor, time, action, validation outcome, and active-version transition.

#### Scenario: Operator rolls back a policy

- **WHEN** an authorized operator selects a previous validated policy version and confirms rollback
- **THEN** the system SHALL activate that version as a new transition
- **AND** SHALL record the rollback in the audit history
- **AND** SHALL show which version is now active

#### Scenario: Decision uses an active policy

- **WHEN** the decision engine evaluates a new request
- **THEN** it SHALL use one complete validated active policy version for the evaluation
- **AND** SHALL not use a partially saved or concurrently replaced policy
