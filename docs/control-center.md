# Control Center operator guide

The Control Center at `http://localhost:3000` is the single operator entrypoint for the local RetentionOps stack. It keeps specialist tools available, but groups the everyday workflow into six task areas:

| Area | Use it for |
| --- | --- |
| Overview | Check service health, model readiness, recent decisions, and key signals. |
| Decisions | Test a customer profile and understand the recommended retention action. |
| Monitoring | Review API traffic and production drift signals. |
| Simulation Lab | Create synthetic drift, compare champion predictions before and after it, and download temporary paired results. |
| Operations | Start only approved training, registration, drift, or feedback jobs. |
| Policy | Review, preview, activate, and roll back decision rules. |

## Decision language

- **Uplift** is the estimated difference in retention caused by offering treatment instead of doing nothing.
- **Expected value** is the uplift multiplied by the estimated customer value, minus treatment cost.
- **Estimated customer value** is an operator-provided assumption used for ROI calculations. It is not automatically observed by the model.
- **Recommendation** is the highest-priority action that passes the active policy thresholds.
- Model attributes appear under **Advanced customer attributes**. The current `f0`–`f10` names are honest fallbacks until the training data dictionary provides business names.

Technical references, decision IDs, model run references, and bounded job diagnostics are hidden under **Technical details** so that the normal workflow remains readable without removing troubleshooting context.

## Drift language

Drift means that recent customer input data has a different distribution from the reference data used to assess the model. It is a monitoring signal, not proof that the model is broken and not an automatic retraining command. Production drift is shown separately from Simulation Lab.

## Simulation Lab

Use Simulation Lab when you need a controlled demonstration or test dataset:

1. Choose a small, moderate, or large change, or open the advanced controls to select individual customer attributes.
2. Choose the number of test records and run the scenario.
3. When the synthetic data is ready, choose **Model-only comparison** to compare predicted uplift, or **Include recommendation comparison** to also compare policy recommendations.
4. For recommendation comparison, provide an **Illustrative customer value**. This is a business assumption for the test only; it is not learned by the model and does not change production policy.
5. Review before/after uplift, changed recommendations, action distribution, expected value, and ROI when enabled. Download the paired Parquet or CSV result if needed.

Simulation Lab results are temporary and isolated. They do not create production decisions, decision logs, feedback records, Prometheus production metrics, retraining jobs, or production drift reports. They are stored in the simulation Docker volume until expiry and use synthetic row identifiers.
The simulator reads the configured baseline but never changes it, starts training, registers a model, or creates a production drift report. Generated Parquet files are stored temporarily in the `drift_simulation_data` Docker volume. In the default local demo mode, PostgreSQL is not used for decision, feedback, operation, simulation, or prediction history; only policy versions remain durable. Files are removed after `DRIFT_SIMULATION_RETENTION_SECONDS`; an expired download is not recreated automatically.

The current feature names are shown as **Customer attribute 1–11** because the model data dictionary has not assigned business names yet. Percentage changes multiply an attribute's values; fixed shifts add the specified amount.

To initialize the metadata table and run cleanup explicitly:

```powershell
docker compose exec ops python -m src.db.migrate_simulations
```

The command is safe to repeat and does not remove PostgreSQL, MLflow, Grafana, or dataset volumes.

## Explicit production drift analysis

Simulation is intentionally separate from production analysis. If a generated artifact needs formal drift analysis, an operator must explicitly provide that artifact to the existing `src.monitoring.drift_report` workflow. The simulator does not expose raw HTML/JSON reports in its primary UI and does not treat a test scenario as evidence about production.

## Policy management

The Policy page shows the active action rules and global limits. Values are validated before activation:

- costs and expected-value thresholds cannot be negative;
- uplift thresholds must be between 0 and 1;
- offer priorities must be unique;
- the `no_action` rule must have zero cost;
- a policy must contain at least one offer.

Set the following values in `.env` to enable the protected workflow:

```dotenv
OPS_ADMIN_TOKEN=use-a-local-secret
POLICY_STORE_ENABLED=true
```

PostgreSQL stores immutable policy versions. In durable mode it also stores policy audit records. A proposed version can be validated and previewed against recent decision logs before activation. Every activation creates a new version, and rollback creates a new transition to the selected prior configuration. If the policy store is not initialized, the Control Center shows the YAML configuration as read-only fallback.

## Demo-local history

The Docker Compose default sets `DEMO_LOCAL_HISTORY=true`. Compact decision summaries, synthetic feedback, and completed Simulation Lab summaries are stored in `localStorage` for the current browser profile only. Raw features, credentials, logs, Parquet files, and CSV files are never placed in browser storage. The store is versioned, bounded, and safe to clear from the Decisions or Simulation Lab page.

This history disappears when the browser site data is cleared, when the operator changes browser profiles, or when the server is restarted before an active simulation completes. Download files remain temporary server artifacts and can expire independently of the browser summary. Set `DEMO_LOCAL_HISTORY=false` to use the existing PostgreSQL-backed durable operation and result history path; this is the mode to use when testing production-like audit behavior.

Synthetic feedback is a demonstration of the delayed-outcome workflow. It is generated from saved decision summaries and must not be interpreted as observed customer behavior.

## Deployment safety

Policy tables are additive and are created by the existing database initialization path. Existing `postgres_data`, `mlflow_data`, and `grafana_data` named volumes are not removed or recreated. Do not run `docker compose down -v` unless deleting persistent data is intentional.

To initialize or re-check the policy tables explicitly:

```powershell
docker compose --profile jobs run --rm jobs python -m src.db.migrate_policy
```
