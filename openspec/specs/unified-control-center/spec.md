## Purpose

Provide a single Dockerized operator entrypoint for the RetentionOps uplift platform while keeping specialist tools available through deep links.

## Requirements

### Requirement: Unified dashboard entrypoint

The system SHALL provide a Dockerized Next.js Control Center as the primary operator-facing entrypoint for the RetentionOps stack.

#### Scenario: Operator opens the control center

- **WHEN** an operator navigates to the configured web entrypoint
- **THEN** the system SHALL render a dashboard without requiring the operator to open separate service UIs for the core overview
- **AND** the dashboard SHALL identify the current environment and refresh state

### Requirement: Service health overview

The Control Center SHALL display the health and availability of the API, PostgreSQL, MLflow, Prometheus, Grafana, and operations services.

#### Scenario: All services are healthy

- **WHEN** all configured service health checks succeed
- **THEN** the dashboard SHALL show a healthy state for each service
- **AND** SHALL show the last successful check time

#### Scenario: A service is unavailable

- **WHEN** a configured service health check fails or times out
- **THEN** the dashboard SHALL show that service as unavailable
- **AND** SHALL display a non-sensitive failure reason or timeout state
- **AND** SHALL keep the rest of the dashboard available when possible

### Requirement: Model status and specialist links

The Control Center SHALL display the loaded model name, alias, version or run identifier, and model-loaded state using the configured MLflow/API integrations.

#### Scenario: Champion model is loaded

- **WHEN** the API reports a loaded `uplift_model@champion`
- **THEN** the dashboard SHALL show the model as ready
- **AND** SHALL show a link to the corresponding MLflow model or run view

#### Scenario: Model is unavailable

- **WHEN** the model cannot be loaded or the model information request fails
- **THEN** the dashboard SHALL show a model-not-ready state
- **AND** SHALL not present the decision playground as operational

### Requirement: Decision playground

The Control Center SHALL provide a form for submitting a valid decision request to FastAPI and SHALL present the decision response in business-readable terms.

#### Scenario: Successful decision request

- **WHEN** an operator submits a valid user ID, customer value, and feature payload
- **THEN** the dashboard SHALL call the decision API
- **AND** SHALL show treatment probability, control probability, uplift score, expected incremental value, ROI, recommended action, and decision reason
- **AND** SHALL display the decision identifier

#### Scenario: Invalid decision request

- **WHEN** required features or customer values are missing or invalid
- **THEN** the dashboard SHALL show field-level or API validation feedback
- **AND** SHALL not display the result as a successful decision

### Requirement: Monitoring and drift summary

The Control Center SHALL display selected Prometheus metrics and the latest drift/retraining summary without requiring direct browser access to Prometheus or the report filesystem.

#### Scenario: Dashboard refreshes metrics

- **WHEN** the configured refresh interval elapses
- **THEN** the dashboard SHALL request bounded metric data through the server-side integration
- **AND** SHALL render request rate, latency, error rate, action distribution, average uplift, and expected value when data is available

#### Scenario: Latest drift report exists

- **WHEN** a valid drift summary is available
- **THEN** the dashboard SHALL show drifted feature count, drift share, retraining recommendation, and retraining reasons
- **AND** SHALL provide a link to the detailed report when configured

### Requirement: Server-side integration boundary

The system SHALL keep PostgreSQL, Prometheus, MLflow, and Docker control calls behind server-side Next.js or control-plane integrations.

#### Scenario: Browser loads dashboard data

- **WHEN** the browser requests dashboard data
- **THEN** it SHALL call the web application origin
- **AND** internal service hostnames, database credentials, and job runner credentials SHALL not be exposed in browser payloads

### Requirement: Specialist tool navigation

The Control Center SHALL provide deep links to Grafana and MLflow for detailed investigation without claiming to replace their specialist UIs.

#### Scenario: Operator investigates a metric or model

- **WHEN** an operator selects a Grafana or MLflow link
- **THEN** the system SHALL open the configured specialist URL for the current environment
- **AND** SHALL preserve the relevant model, dashboard, or time-window context when the target supports it

### Requirement: Docker deployment

The Control Center SHALL run as a Compose service with a health check and SHALL not require destructive changes to existing PostgreSQL, MLflow, Grafana, or dataset volumes.

#### Scenario: Stack starts with existing volumes

- **WHEN** the operator starts the updated Compose stack
- **THEN** the web service SHALL become healthy after its dependencies are available
- **AND** existing named volumes SHALL remain attached and readable
- **AND** Grafana SHALL remain reachable on its configured alternate host port
