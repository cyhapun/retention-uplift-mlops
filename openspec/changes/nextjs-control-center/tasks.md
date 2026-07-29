## 1. Platform and service setup

- [x] 1.1 Create the `web/` Next.js App Router application with TypeScript, production scripts, and standalone Docker output.
- [x] 1.2 Add a multi-stage Next.js Dockerfile with a non-development runtime and `/health` endpoint.
- [x] 1.3 Add the `web` service to Docker Compose with internal API URLs, health checks, and host port `3000`.
- [x] 1.4 Move Grafana to host port `3001` while preserving its container port and `grafana_data` volume.
- [x] 1.5 Add the `ops` control-plane service, environment variables, health check, and dependency conditions without changing existing data volumes.

## 2. Control-plane read models

- [x] 2.1 Define versioned response models for overview, service health, model status, metrics, drift, decisions, feedback, and specialist links.
- [x] 2.2 Implement service health aggregation for API, PostgreSQL, MLflow, Prometheus, Grafana, and ops with timeouts and partial-failure handling.
- [x] 2.3 Implement model summary integration using the FastAPI model endpoint and MLflow metadata, including champion alias and deep links.
- [x] 2.4 Implement bounded Prometheus instant/range query adapters for request rate, latency, errors, action distribution, uplift, and expected value.
- [x] 2.5 Implement PostgreSQL summary queries for decision counts, action distribution, feedback counts, observed outcome rate, and realized value.
- [x] 2.6 Implement drift summary reading with safe handling for missing or malformed report files.
- [x] 2.7 Expose read-only dashboard endpoints through the control plane and add response/error tests.

## 3. Operations control plane

- [x] 3.1 Add persistent operation/job and audit models with status, timestamps, actor, operation name, exit information, and bounded output metadata.
- [x] 3.2 Implement an allowlisted operation registry for training, model registration, drift reporting, drift simulation, and feedback simulation.
- [x] 3.3 Implement single-concurrency or configured queue behavior and duplicate-operation protection.
- [x] 3.4 Implement subprocess execution with fixed module/argument mappings, timeout handling, output capture, and non-zero exit handling.
- [x] 3.5 Add configurable admin authorization and reject mutating requests when authorization is not configured or invalid.
- [x] 3.6 Add startup reconciliation for stale running jobs and expose job list/detail endpoints.
- [x] 3.7 Verify that the web and ops containers do not mount or access the Docker socket.

## 4. Next.js Control Center UI

- [x] 4.1 Create the dashboard shell with navigation, environment label, refresh controls, loading states, and error boundaries.
- [x] 4.2 Build the system overview with service health cards, model readiness, decision/feedback counts, and specialist-tool links.
- [x] 4.3 Build the decision playground with validated feature input, API submission, result cards, and business-readable decision reasons.
- [x] 4.4 Build model, monitoring, and drift sections using server-side dashboard routes and bounded refresh intervals.
- [x] 4.5 Build decision history, feedback summary, and job status views with empty/error states.
- [x] 4.6 Add authorized operation controls with confirmation states, progress updates, failure summaries, and audit references.
- [x] 4.7 Add responsive layout and accessible status/error patterns for the primary dashboard workflows.

## 5. Verification and deployment

- [x] 5.1 Add control-plane unit tests for upstream failures, authorization, allowlisting, duplicate protection, job transitions, and stale-job recovery.
- [x] 5.2 Add frontend tests for dashboard loading, partial service failure, decision submission, metrics rendering, drift rendering, and protected operations.
- [x] 5.3 Add Docker Compose validation and integration smoke tests for web health, API decision flow, model summary, and preserved volumes.
- [x] 5.4 Update README and demo documentation with the single dashboard URL, port mappings, environment variables, job safety rules, and rollback steps.
- [x] 5.5 Run Ruff, formatting checks, Python tests, frontend tests, `docker compose config`, and Docker image builds.
