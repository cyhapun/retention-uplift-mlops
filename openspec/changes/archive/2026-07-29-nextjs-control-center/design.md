## Context

RetentionOps currently runs as a Docker Compose stack containing PostgreSQL, MLflow, FastAPI, Prometheus, Grafana, and one-off jobs. The FastAPI service exposes health, model information, decision, and Prometheus metrics endpoints. Grafana is provisioned with a Prometheus datasource and an operational dashboard, while drift reports are written to `reports/drift/` and MLflow owns experiment and model registry data.

There is no web application that presents these systems together, no normalized dashboard API, and no safe control-plane for launching the existing training, registration, drift, and feedback jobs. The new design must support a single operator entrypoint without coupling the browser directly to internal services or exposing the Docker socket.

## Goals / Non-Goals

**Goals:**

- Provide a Dockerized Next.js Control Center as the primary local UI.
- Present service health, model state, decision results, monitoring metrics, drift summaries, feedback summaries, and specialist-tool links in one coherent dashboard.
- Keep FastAPI as the source of truth for decision inference and policy behavior.
- Add server-side aggregation so browser clients do not access PostgreSQL, MLflow, Prometheus, or Docker directly.
- Provide an authenticated, allowlisted operations surface for MLOps jobs with persisted status and audit information.
- Preserve existing PostgreSQL, MLflow, Grafana, and dataset volumes.
- Keep the implementation compatible with Docker Compose and the current PowerShell workflow.

**Non-Goals:**

- Replace MLflow's experiment/model registry UI.
- Replace Grafana's advanced time-series exploration.
- Change the uplift model, policy thresholds, drift algorithm, or feedback simulation semantics.
- Introduce automatic retraining from a drift signal.
- Expose arbitrary shell commands or Docker control to the browser.
- Define a production identity provider; the first implementation only needs a configurable local admin boundary.

## Decisions

### 1. Use Next.js as the primary UI and BFF

Add a `web/` Next.js application using the App Router and a production Docker image with standalone output. Server components and route handlers will call internal services over the Compose network. Browser requests will target the Next.js origin, which avoids browser-visible internal hostnames and keeps CORS and service credentials server-side.

Alternative considered: serving HTML directly from FastAPI. This would minimize containers but would make the operational UI less maintainable and limit the dashboard interaction model. A separate Next.js application better matches the unified product goal.

### 2. Separate decision API from operations control

Keep the existing `api` service focused on inference, policy, decision logging, and metrics. Add an `ops` control-plane service for dashboard aggregation and protected operations. The control plane may reuse the existing Python package and Docker image, but it owns operator-only endpoints and job lifecycle handling.

Alternative considered: adding all admin endpoints to the existing FastAPI app. This is simpler initially but mixes customer-facing inference with privileged operations and makes authorization boundaries harder to reason about.

### 3. Use service APIs and repository queries, not browser-side database access

The control plane will normalize data from:

- FastAPI for health, model metadata, and decisions.
- Prometheus HTTP API for time-series metrics.
- MLflow tracking/model registry APIs for model and run summaries.
- PostgreSQL through existing SQLAlchemy models/repositories for decision and feedback summaries.
- Drift summary JSON files for the latest report and retraining recommendation.

The Next.js UI will consume stable control-plane contracts such as `/dashboard/overview`, `/dashboard/metrics`, `/dashboard/model`, `/dashboard/drift`, and `/dashboard/decisions`.

### 4. Use allowlisted background jobs without a Docker socket

The `ops` service will expose named operations rather than arbitrary commands. Initial operations are training, model registration, drift report generation, drift simulation, and feedback simulation. Each job is persisted with an ID, operation name, status, timestamps, exit information, and an operator identity. Execution uses known Python module arguments inside the operations container; the UI never receives Docker host access.

Alternative considered: mounting `/var/run/docker.sock` into the UI or API. This would give a compromised web process broad host-level control and is rejected.

### 5. Make Grafana and MLflow specialist surfaces, not primary embedded pages

The Control Center will show summary cards and deep links to Grafana and MLflow. Selected Grafana panels may be embedded later if the local authentication and frame policies are explicitly configured. MLflow will use links because its security middleware may apply clickjacking/CORS protections and its UI is already a complete specialist surface.

### 6. Keep local port separation and internal networking

Next.js will use host port `3000`. Grafana will move to host port `3001` while remaining on container port `3000`. MLflow and API ports may remain published for local debugging, but production deployment should expose only the web/reverse-proxy entrypoint. All services remain on the internal Compose network.

### 7. Add a configurable local authorization boundary

Read-only dashboard access can remain available for local development. Mutating operations require a configured admin token or equivalent local authentication setting. The control plane must reject mutating requests when the protection is not configured, and every accepted operation must create an audit record.

## Risks / Trade-offs

- [Risk] The new web and ops services increase deployment complexity. → Keep both on the existing Python/Docker Compose workflow, use health checks, and provide one bootstrap command.
- [Risk] Prometheus/MLflow/PostgreSQL response formats can change independently. → Normalize them behind versioned control-plane response models and test adapters with mocked upstream responses.
- [Risk] Background jobs can outlive an HTTP request or fail during container restart. → Persist job state, record subprocess output, mark stale running jobs after startup, and keep the first worker single-concurrency.
- [Risk] A local admin token is not a complete production identity solution. → Make the boundary explicit, keep mutating controls disabled without configuration, and defer OIDC/SSO to a later change.
- [Risk] SQLite-backed MLflow metadata in a named volume is not ideal for concurrent production use. → Preserve the current local setup for this change and plan PostgreSQL-backed MLflow plus object storage for production scale.
- [Risk] Dashboard polling can overload internal services. → Use bounded refresh intervals, server-side caching for slow summaries, and Prometheus range queries with explicit time windows.
- [Risk] UI and specialist links can expose internal ports in local mode. → Generate environment-based URLs and publish only the web entrypoint in production.

## Migration Plan

1. Add the Next.js web service, Dockerfile, environment variables, and health check.
2. Add the ops control-plane service and its read-only aggregation endpoints.
3. Add dashboard response models, database summary queries, and drift report readers.
4. Add the operations job table, allowlisted runner, authorization boundary, and audit records.
5. Update Compose ports so Next.js owns host port `3000` and Grafana uses host port `3001`.
6. Start the stack with existing named volumes unchanged; no data copy or destructive volume operation is required.
7. Validate health endpoints, decision playground behavior, metrics rendering, model summary, drift summary, and safe job rejection/execution.

Rollback is to stop/remove the `web` and `ops` services and restore the previous host port mapping. Existing API, MLflow, PostgreSQL, Prometheus, Grafana, and data volumes remain usable. If the operations schema has been created, leaving the additive table in place is safe; no existing tables or data are removed.

## Open Questions

- Should local mutating operations use a static admin token or a small username/password login before production authentication is designed?
- Should the first dashboard render charts with a Next.js chart library, Grafana panel embeds, or a combination of both?
- Should the `ops` service run one job at a time or use a durable queue from the first implementation?
- Which production environment and object store should be targeted for a future PostgreSQL-backed MLflow deployment?
