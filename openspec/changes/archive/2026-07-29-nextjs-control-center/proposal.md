## Why

RetentionOps currently exposes useful capabilities through separate FastAPI, MLflow, Prometheus, Grafana, PostgreSQL, and Docker job interfaces. This makes it difficult to understand system health, inspect model behavior, run a decision demo, review drift, and operate MLOps jobs from one place.

The project needs a single, role-aware Next.js control center that presents the operational state coherently while preserving the existing specialized services behind internal APIs.

## What Changes

- Add a Dockerized Next.js web application as the primary user entrypoint.
- Add a unified dashboard for service health, model state, decision outcomes, drift status, feedback summaries, and monitoring metrics.
- Add a decision playground that calls the existing FastAPI `/decide-action` endpoint and presents uplift, ROI, and recommended action results.
- Add server-side dashboard aggregation APIs so the browser does not access PostgreSQL, Prometheus, MLflow, or Docker directly.
- Add safe operational controls for allowlisted training, registration, drift, and feedback jobs.
- Track job status, failures, and operator actions for operational visibility.
- Add authentication/authorization boundaries before enabling mutating controls.
- Keep Grafana and MLflow available as deep-linked specialist interfaces rather than replacing them.
- Re-map local host ports so Next.js is the single primary dashboard entrypoint while Grafana remains available for advanced monitoring.
- Preserve existing PostgreSQL, MLflow, Grafana, and dataset volumes.

## Capabilities

### New Capabilities

- `unified-control-center`: Next.js dashboard for system overview, service health, model information, decision demonstrations, monitoring summaries, drift results, and links to specialist tools.
- `operations-control`: Authenticated and audited control-plane actions for running approved MLOps jobs and tracking their status without exposing the Docker socket to the UI.

### Modified Capabilities

<!-- No existing OpenSpec capabilities are defined under openspec/specs/. -->

## Impact

- Add a new `web/` Next.js application and Docker image.
- Extend FastAPI with dashboard aggregation and protected operations endpoints, or add a dedicated control-plane service where isolation is required.
- Add API contracts for health summaries, model summaries, Prometheus queries, drift summaries, decision history, and job status.
- Update `docker-compose.yml`, environment examples, port mappings, health checks, and deployment documentation.
- Keep Prometheus, Grafana, MLflow, PostgreSQL, and jobs as separate services on the internal Docker network.
- Add frontend and backend tests plus Docker Compose validation.
- No model-training algorithm or policy behavior changes are required by this proposal.
