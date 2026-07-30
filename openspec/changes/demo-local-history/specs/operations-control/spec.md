## MODIFIED Requirements

### Requirement: Allowlisted operations

The operations control plane SHALL expose only named, allowlisted MLOps operations, simulation requests, and simulation prediction requests, SHALL validate operation-specific parameters, and SHALL reject arbitrary shell commands, arbitrary module paths, and unrecognized arguments. In demo-local history mode, transient operation state MAY be held in process memory and SHALL not require durable operation-history writes.

#### Scenario: Approved operation is requested

- **WHEN** an authorized operator requests a supported training, registration, drift, feedback, drift simulation, or simulation prediction operation
- **THEN** the control plane SHALL validate the operation-specific arguments
- **AND** SHALL start only the corresponding approved implementation
- **AND** SHALL create durable operation metadata only when durable history mode is enabled

#### Scenario: Unsupported operation is requested

- **WHEN** a request contains an unknown operation, arbitrary path, unsupported model reference, or unrecognized argument
- **THEN** the control plane SHALL reject the request
- **AND** SHALL not start a subprocess or prediction worker
- **AND** SHALL record the rejection reason when an authenticated identity is available and durable audit mode is enabled

### Requirement: Job lifecycle and status

The control plane SHALL expose operation or prediction identity, status, timestamps, completion information, bounded output references, and structured results while allowing demo-local mode to keep this state transient rather than persisting it in PostgreSQL.

#### Scenario: Job succeeds

- **WHEN** an approved operation completes with exit code zero
- **THEN** the job SHALL transition to `succeeded`
- **AND** the dashboard SHALL show completion time and a concise result summary
- **AND** the state MAY be lost after a control-plane restart in demo-local mode

#### Scenario: Simulation prediction succeeds

- **WHEN** an approved simulation prediction completes successfully
- **THEN** the prediction SHALL transition to `succeeded`
- **AND** the dashboard SHALL show a concise comparison summary and result expiry
- **AND** the result SHALL be available only through the protected download boundary
- **AND** the completed compact summary SHALL be available for browser-local history

#### Scenario: Job or prediction fails

- **WHEN** an approved operation or simulation prediction exits non-zero or raises an execution error
- **THEN** the job or prediction SHALL transition to `failed`
- **AND** the dashboard SHALL show a non-sensitive failure summary
- **AND** any partial result artifact SHALL be removed or marked unavailable

#### Scenario: Control-plane restarts during a job

- **WHEN** the control-plane service restarts while a job is marked `running`
- **THEN** durable mode SHALL reconcile or mark stale jobs according to the configured recovery policy
- **AND** demo-local mode SHALL show the job as unavailable or retryable
- **AND** neither mode SHALL report an unverified job as successfully completed

#### Scenario: Control-plane restarts during a prediction

- **WHEN** the control-plane service restarts while a simulation prediction is marked `queued` or `running`
- **THEN** durable mode SHALL reconcile or mark the prediction stale according to the configured recovery policy
- **AND** demo-local mode SHALL show the prediction as unavailable or retryable
- **AND** neither mode SHALL report an unverified prediction as successfully completed

## ADDED Requirements

### Requirement: Demo-local persistence boundary

The control plane SHALL support an explicitly configured demo-local mode that keeps decision, feedback, simulation, and operation history out of durable PostgreSQL while retaining protected policy-version storage.

#### Scenario: Demo-local mode is enabled

- **WHEN** the stack starts with demo-local history enabled
- **THEN** the control plane SHALL not require `decision_logs`, `feedback_logs`, `operation_runs`, `operation_audits`, `simulation_runs`, or `simulation_prediction_runs` writes for the demo workflow
- **AND** SHALL continue to enforce admin authorization for protected operations and policy changes

#### Scenario: Durable mode is enabled

- **WHEN** the stack starts with demo-local history disabled
- **THEN** existing durable persistence and audit behavior SHALL remain available
- **AND** the browser-local history feature SHALL remain an optional presentation layer
