## Purpose

Provide a safe, authenticated control plane for running named RetentionOps MLOps operations without exposing arbitrary shell or Docker host control.

## Requirements

### Requirement: Allowlisted operations

The operations control plane SHALL expose only named, allowlisted MLOps operations and SHALL reject arbitrary shell commands, arbitrary module paths, and unrecognized arguments.

#### Scenario: Approved operation is requested

- **WHEN** an authorized operator requests a supported training, registration, drift, or feedback operation
- **THEN** the control plane SHALL validate the operation-specific arguments
- **AND** SHALL create a persisted job record
- **AND** SHALL start the corresponding approved command

#### Scenario: Unsupported operation is requested

- **WHEN** a request contains an unknown operation or disallowed argument
- **THEN** the control plane SHALL reject the request
- **AND** SHALL not start a subprocess
- **AND** SHALL record the rejection reason when an authenticated identity is available

### Requirement: Job lifecycle and status

The control plane SHALL persist job identity, operation, status, timestamps, exit information, and a bounded reference to execution output.

#### Scenario: Job succeeds

- **WHEN** an approved operation completes with exit code zero
- **THEN** the job SHALL transition to `succeeded`
- **AND** the dashboard SHALL show completion time and a concise result summary

#### Scenario: Job fails

- **WHEN** an approved operation exits non-zero or raises an execution error
- **THEN** the job SHALL transition to `failed`
- **AND** the dashboard SHALL show a non-sensitive failure summary
- **AND** the full output SHALL remain available only through an authorized operations view

#### Scenario: Control-plane restarts during a job

- **WHEN** the control-plane service restarts while a job is marked `running`
- **THEN** the service SHALL reconcile or mark stale jobs according to the configured recovery policy
- **AND** SHALL not report an unverified job as successfully completed

### Requirement: Authorization for mutating operations

The control plane SHALL require an explicitly configured admin authorization mechanism for mutating operations and SHALL keep those operations disabled when authorization is not configured.

#### Scenario: Authorized operator starts a job

- **WHEN** a request includes valid admin authorization
- **THEN** the control plane SHALL authorize the operation
- **AND** SHALL record the operator identity in the job audit data

#### Scenario: Unauthorized operator starts a job

- **WHEN** a request lacks valid admin authorization
- **THEN** the control plane SHALL return an authorization error
- **AND** SHALL not create or start a job

### Requirement: Audit trail

The control plane SHALL record accepted and rejected mutating operations with actor, operation, request time, status, and outcome metadata.

#### Scenario: Operation is audited

- **WHEN** an authorized operation is accepted or a protected operation is rejected
- **THEN** an audit record SHALL be created without storing secrets or full credentials
- **AND** the record SHALL be queryable by an authorized operator

### Requirement: No Docker host control from the UI

The web application and browser SHALL not receive access to the Docker socket or arbitrary container-management permissions.

#### Scenario: Dashboard requests an operation

- **WHEN** the operator starts a supported job through the dashboard
- **THEN** the request SHALL be handled by the control plane's allowlisted runner
- **AND** the web container SHALL not mount or access the Docker socket

### Requirement: Operational safety

The control plane SHALL enforce single-operation concurrency or an explicit configured queue policy and SHALL prevent duplicate destructive operations from being started concurrently.

#### Scenario: Duplicate operation is submitted

- **WHEN** an equivalent operation is already running and the configured policy disallows duplicates
- **THEN** the control plane SHALL reject or safely deduplicate the new request
- **AND** SHALL explain the existing job identifier to the operator
