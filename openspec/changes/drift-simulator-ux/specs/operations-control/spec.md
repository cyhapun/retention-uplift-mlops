## Purpose

Provide a safe, authenticated control plane for running named RetentionOps MLOps operations without exposing arbitrary shell or Docker host control.

## MODIFIED Requirements

### Requirement: Allowlisted operations

The operations control plane SHALL expose only named, allowlisted MLOps operations and drift simulation requests, SHALL validate operation-specific parameters, and SHALL reject arbitrary shell commands, arbitrary module paths, arbitrary filesystem paths, and unrecognized arguments.

#### Scenario: Approved operation is requested

- **WHEN** an authorized operator requests a supported training, registration, drift analysis, feedback, or parameterized drift simulation operation
- **THEN** the control plane SHALL validate the operation-specific arguments
- **AND** SHALL create a persisted job or simulation record
- **AND** SHALL start only the corresponding approved implementation

#### Scenario: Unsupported simulation parameter is requested

- **WHEN** a request contains an unknown feature, unsupported transformation, arbitrary path, or out-of-range simulation value
- **THEN** the control plane SHALL reject the request
- **AND** SHALL not start a subprocess or create an artifact
- **AND** SHALL record the rejection reason when an authenticated identity is available

### Requirement: Job lifecycle and status

The control plane SHALL persist job or simulation identity, operation, status, timestamps, exit or completion information, a bounded reference to execution output, and a structured result when an operation produces one.

#### Scenario: Simulation succeeds

- **WHEN** an approved drift simulation completes successfully
- **THEN** the simulation SHALL transition to `succeeded`
- **AND** the dashboard SHALL show a concise summary and artifact expiry
- **AND** the generated artifact SHALL be available only through the protected download boundary

#### Scenario: Job fails

- **WHEN** an approved operation or simulation exits non-zero or raises an execution error
- **THEN** the job or simulation SHALL transition to `failed`
- **AND** the dashboard SHALL show a non-sensitive failure summary
- **AND** any partial artifact SHALL be removed or marked unavailable

#### Scenario: Control-plane restarts during a job or simulation

- **WHEN** the control-plane service restarts while a job or simulation is marked `running`
- **THEN** the service SHALL reconcile or mark stale records according to the configured recovery policy
- **AND** SHALL not report an unverified operation as successfully completed

### Requirement: Authorization for mutating operations

The control plane SHALL require an explicitly configured admin authorization mechanism for job operations, policy changes, drift simulation creation, and simulation downloads, and SHALL keep protected actions disabled when authorization is not configured.

#### Scenario: Authorized operator starts a simulation or downloads data

- **WHEN** a request includes valid admin authorization
- **THEN** the control plane SHALL authorize the requested action
- **AND** SHALL record the operator identity in the relevant audit data

#### Scenario: Unauthorized operator starts a simulation or downloads data

- **WHEN** a request lacks valid admin authorization
- **THEN** the control plane SHALL return an authorization error
- **AND** SHALL not create a simulation or stream a protected artifact

### Requirement: Operational safety

The control plane SHALL enforce single-operation concurrency or an explicit configured queue policy, SHALL prevent duplicate destructive operations from being started concurrently, SHALL prevent lost updates to the active policy, and SHALL enforce simulation row, intensity, storage, and expiry limits.

#### Scenario: Duplicate operation is submitted

- **WHEN** an equivalent operation is already running and the configured policy disallows duplicates
- **THEN** the control plane SHALL reject or safely deduplicate the new request
- **AND** SHALL explain the existing job or simulation identifier to the operator

#### Scenario: Simulation exceeds a configured limit

- **WHEN** a simulation request exceeds the configured row count, intensity, file size, or retention limit
- **THEN** the control plane SHALL reject it before dataset generation
- **AND** SHALL leave existing datasets and simulation records unchanged
