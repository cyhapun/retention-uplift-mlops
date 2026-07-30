## MODIFIED Requirements

### Requirement: Allowlisted operations

The operations control plane SHALL expose only named, allowlisted MLOps operations, simulation requests, and simulation prediction requests, SHALL validate operation-specific parameters, and SHALL reject arbitrary shell commands, arbitrary module paths, and unrecognized arguments.

#### Scenario: Approved operation is requested

- **WHEN** an authorized operator requests a supported training, registration, drift, feedback, drift simulation, or simulation prediction operation
- **THEN** the control plane SHALL validate the operation-specific arguments
- **AND** SHALL create a persisted job or simulation prediction record
- **AND** SHALL start only the corresponding approved implementation

#### Scenario: Unsupported operation is requested

- **WHEN** a request contains an unknown operation, arbitrary path, unsupported model reference, or unrecognized argument
- **THEN** the control plane SHALL reject the request
- **AND** SHALL not start a subprocess or prediction worker
- **AND** SHALL record the rejection reason when an authenticated identity is available

### Requirement: Job lifecycle and status

The control plane SHALL persist job or simulation identity, operation, status, timestamps, exit or completion information, a bounded reference to execution output, and a structured result when an operation produces one.

#### Scenario: Simulation prediction succeeds

- **WHEN** an approved simulation prediction completes successfully
- **THEN** the prediction SHALL transition to `succeeded`
- **AND** the dashboard SHALL show a concise comparison summary and result expiry
- **AND** the result SHALL be available only through the protected download boundary

#### Scenario: Job or prediction fails

- **WHEN** an approved operation or simulation prediction exits non-zero or raises an execution error
- **THEN** the job or prediction SHALL transition to `failed`
- **AND** the dashboard SHALL show a non-sensitive failure summary
- **AND** any partial result artifact SHALL be removed or marked unavailable

#### Scenario: Control-plane restarts during a prediction

- **WHEN** the control-plane service restarts while a simulation prediction is marked `queued` or `running`
- **THEN** the service SHALL reconcile or mark the prediction stale according to the configured recovery policy
- **AND** SHALL not report an unverified prediction as successfully completed

### Requirement: Authorization for mutating operations

The control plane SHALL require an explicitly configured admin authorization mechanism for job operations, policy changes, simulation creation, simulation prediction, and simulation result downloads, and SHALL keep protected actions disabled when authorization is not configured.

#### Scenario: Authorized operator starts or downloads a lab run

- **WHEN** a request includes valid admin authorization
- **THEN** the control plane SHALL authorize the requested action
- **AND** SHALL record the operator identity in the relevant audit data

#### Scenario: Unauthorized operator starts or downloads a lab run

- **WHEN** a request lacks valid admin authorization
- **THEN** the control plane SHALL return an authorization error
- **AND** SHALL not create a prediction or stream a protected result artifact

### Requirement: Audit trail

The control plane SHALL record accepted and rejected mutating operations, including jobs, simulations, prediction runs, and policy changes, with actor, operation, request time, status, and outcome metadata.

#### Scenario: Prediction action is audited

- **WHEN** a simulation prediction is accepted, rejected, fails, expires, or is downloaded
- **THEN** an audit record SHALL be created without storing secrets or full credentials
- **AND** the record SHALL identify the related simulation or prediction run

### Requirement: Operational safety

The control plane SHALL enforce single-operation concurrency or an explicit configured queue policy, SHALL prevent duplicate destructive operations from being started concurrently, SHALL prevent lost updates to the active policy, and SHALL enforce simulation prediction row, batch, storage, model, and expiry limits.

#### Scenario: Duplicate prediction is submitted

- **WHEN** an equivalent prediction is already running and the configured policy disallows duplicates
- **THEN** the control plane SHALL reject or safely deduplicate the new request
- **AND** SHALL explain the existing prediction identifier to the operator

#### Scenario: Prediction exceeds a configured limit

- **WHEN** a prediction request exceeds the configured row, batch, output-size, or retention limit
- **THEN** the control plane SHALL reject it before model inference
- **AND** SHALL leave existing datasets, results, and records unchanged

## ADDED Requirements

### Requirement: Production-path isolation

The control plane SHALL execute Simulation Lab inference without using the production decision logging, feedback, or Prometheus decision-metric paths.

#### Scenario: Lab inference is executed

- **WHEN** a prediction worker scores a synthetic scenario
- **THEN** it SHALL use an isolated batch predictor or explicitly simulation-marked internal path
- **AND** SHALL not create `DecisionLog` or `FeedbackLog` records
- **AND** SHALL not invoke training, registration, or production drift-report operations
