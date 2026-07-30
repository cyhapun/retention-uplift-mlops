## Context

The current simulator is a fixed helper that multiplies `f0`, adds to `f3`, and scales `f7`, then overwrites one predictable output path. The generic operations runner exposes it as a button, but the UI has no way to choose features or intensity, no structured result to display, and no download endpoint. The separate drift-report command reads a fixed baseline path, so simulation and analysis are not a coherent workflow.

The desired workflow is an operator-controlled demo and test utility. It must create a new dataset without changing the reference or baseline datasets, show a concise comparison summary, and make the generated data downloadable on demand. It must not turn a simulation into production retraining or expose host paths through the browser.

## Goals / Non-Goals

### Goals

- Allow safe preset and per-feature drift configuration from the Control Center.
- Generate uniquely identified Parquet datasets and provide CSV downloads without writing generated files into the source tree.
- Return a plain-language summary of affected features, before/after statistics, row count, and drift severity.
- Persist simulation metadata and status while retaining generated files only for a configurable short period.
- Keep the actual production drift report as a separate explicit workflow.
- Protect resource use, paths, parameters, and downloads through the existing operations authorization boundary.

### Non-Goals

- Changing production reference data, test data, model artifacts, or the decision policy.
- Automatically running Evidently HTML/JSON reports after every simulation.
- Automatically retraining or registering a model.
- Supporting arbitrary Python expressions, arbitrary filesystem paths, or arbitrary subprocess arguments.
- Building a general-purpose synthetic-data platform.

## Decisions

### 1. Use a dedicated simulation API and service

The Control Center will call server-side simulation endpoints rather than passing parameters to a generic shell command. The ops service will validate a typed request, create a simulation record, run the approved simulation service in its bounded worker, and expose status, summary, and download endpoints.

This keeps user input out of shell construction and allows structured results. Reusing the existing fixed `OperationRunner` command is rejected because it only accepts static commands, stores unstructured output, and cannot safely express per-feature parameters.

### 2. Support presets plus bounded advanced controls

The request will support named presets such as low, medium, and high drift, plus an explicit list of feature transformations. A transformation will use an allowlisted feature name and one of two operations: percentage scaling or absolute shift. Each operation has configured minimum and maximum intensity. The server will cap row count and reject unknown features, duplicate feature definitions, unsupported operations, and out-of-range values.

Presets make the common demo path understandable; advanced controls make the simulator useful for testing. Free-form formulas are rejected because they are hard to validate and create an unnecessary code-execution surface.

### 3. Keep a canonical Parquet artifact and convert CSV on request

The simulation service will write one uniquely named Parquet artifact under a configurable simulation root. The CSV download will be generated from that artifact when requested, with bounded output size and the same authorization check. The simulation record will expose opaque IDs and download routes, never host paths.

Storing only the canonical Parquet file avoids keeping duplicate artifacts. Streaming or temporary conversion is preferred over permanently storing both formats.

### 4. Use PostgreSQL for metadata and a named Docker volume for files

PostgreSQL will store simulation ID, status, request parameters, affected features, summary metrics, created/expired timestamps, actor, and artifact metadata. Generated datasets will live in a dedicated named volume mounted only by the ops service, for example `/var/lib/retentionops/simulations`.

The volume is appropriate for generated files that must survive an ops container restart but do not belong in the source tree. The database is not used to store Parquet or CSV bytes. A future object-store adapter can replace the volume without changing the UI contract.

### 5. Apply retention and cleanup explicitly

Each simulation receives an expiry time from `DRIFT_SIMULATION_RETENTION_SECONDS`. Cleanup will run at ops startup and before/after simulation creation, deleting only artifacts belonging to expired simulation records. Downloads after expiry return a clear not-found/expired response. Metadata may remain as a short audit history or be pruned by a separate retention setting.

### 6. Separate simulation summary from production drift monitoring

The simulation response will use the existing pure feature-statistics calculation to report the expected changes and a simple severity classification. It will not write `reports/drift/` or trigger the detailed drift-report operation. The Monitoring page will label the result as simulated data and keep the production drift signal separate.

An operator may later choose an explicit “Analyze this simulation” action. That action can invoke the existing drift-report workflow with the simulation artifact as input, but it is intentionally outside the default simulation path.

### 7. Keep the browser behind Next.js routes

Next.js server-side routes will proxy create/status/download requests to ops and keep the admin token and internal filesystem path server-side. The download route will stream the response with a safe filename and content type. The browser will receive only the summary and an opaque download URL.

## Risks / Trade-offs

- [Risk] Large datasets can consume the simulation volume quickly → enforce row/file limits, configurable TTL, cleanup on startup, and clear storage usage in the UI.
- [Risk] A simulation can be mistaken for evidence of production drift → label every result as simulated and keep it out of the production drift card by default.
- [Risk] CSV conversion can be expensive → convert on demand with a bounded response and avoid storing duplicate CSV artifacts.
- [Risk] Feature names are currently `f0`–`f10` → show friendly fallback labels and preserve the raw feature key only in technical details.
- [Risk] Ops restarts during generation can leave an incomplete file → write to a temporary path, atomically finalize it, and reconcile `running` records as failed.
- [Risk] Concurrent downloads or simulations can increase resource use → use the existing single-worker safety policy for generation and bounded download/cleanup operations.

## Migration Plan

1. Add typed simulation request/result contracts, validation, pure transformation helpers, and summary calculation while preserving the existing helper behavior as a default preset.
2. Add simulation metadata tables, named volume configuration, retention settings, and an ops service with create/status/download endpoints.
3. Add Next.js proxy routes and replace the generic simulation button with the guided simulator panel.
4. Add tests for validation, transformations, summary accuracy, expiry, authorization, download formats, and restart recovery.
5. Verify the existing detailed drift-report operation and baseline reports remain unchanged; deploy with the new named volume and retention configuration.

Rollback is additive: stop exposing the new UI routes and disable simulation endpoints while retaining existing baseline and detailed drift-report behavior. Expired simulation artifacts can be removed without touching persistent PostgreSQL, MLflow, Grafana, or dataset volumes.

## Open Questions

- Should the simulator offer only the current `f0`–`f10` attributes initially, or also expose business metadata once the training data dictionary is approved?
- What default retention period and maximum row count are appropriate for the Docker Desktop demo environment?
- Should “Analyze this simulation” be included in the first implementation or deferred to a follow-up change?
