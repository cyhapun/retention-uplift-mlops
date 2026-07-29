# Control Center operator guide

The Control Center at `http://localhost:3000` is the single operator entrypoint for the local RetentionOps stack. It keeps specialist tools available, but groups the everyday workflow into five task areas:

| Area | Use it for |
| --- | --- |
| Overview | Check service health, model readiness, recent decisions, and key signals. |
| Decisions | Test a customer profile and understand the recommended retention action. |
| Monitoring | Review API traffic, service health, and input-data drift. |
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

Drift means that recent customer input data has a different distribution from the reference data used to assess the model. It is a monitoring signal, not proof that the model is broken and not an automatic retraining command. Use the Monitoring page to inspect the affected attributes, then use Operations to run a report or retraining workflow when the team has reviewed the signal.

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

PostgreSQL stores immutable policy versions and audit records. A proposed version can be validated and previewed against recent decision logs before activation. Every activation creates a new version, and rollback creates a new transition to the selected prior configuration. If the policy store is not initialized, the Control Center shows the YAML configuration as read-only fallback.

## Deployment safety

Policy tables are additive and are created by the existing database initialization path. Existing `postgres_data`, `mlflow_data`, and `grafana_data` named volumes are not removed or recreated. Do not run `docker compose down -v` unless deleting persistent data is intentional.

To initialize or re-check the policy tables explicitly:

```powershell
docker compose --profile jobs run --rm jobs python -m src.db.migrate_policy
```
