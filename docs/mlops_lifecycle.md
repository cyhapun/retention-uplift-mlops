# MLOps Lifecycle

RetentionOps demonstrates an end-to-end MLOps lifecycle.

## 1. Data Ingestion

```text
Raw Criteo uplift CSV
→ full-file sampling
→ schema validation
→ train/valid/test/reference datasets
```

## 2. Experimentation

- EDA
- baseline response models
- T-Learner uplift model
- MLflow tracking

## 3. Model Registry

```text
treatment model + control model
→ MLflow PyFunc wrapper
→ registered model
→ alias: champion
```

## 4. Serving

- FastAPI
- MLflow URI: `models:/uplift_model@champion`
- `/decide-action`

## 5. Decisioning

```text
uplift score
→ expected incremental value
→ recommended action
```

## 6. Logging

- `decision_logs`
- `feedback_logs`

## 7. Monitoring

- Prometheus metrics
- Grafana dashboard
- Evidently drift reports

## 8. Feedback

- `decision_logs` are read after the configured delay
- observed outcome is simulated
- realized value is written to `feedback_logs`

Feedback simulation is an offline job. It does not feed the current Policy Engine in real time.

## 9. CI/CD

- GitHub Actions
- ruff
- pytest
- docker compose validation
- containerized tests

## 10. Local Deployment

- Docker Compose
- PostgreSQL
- MLflow
- FastAPI
- Prometheus
- Grafana
- jobs

## Reproducible Run Order

```text
1. Build data
2. Train uplift model
3. Register model and assign champion alias
4. Start FastAPI
5. Generate decisions and inspect logs/metrics
6. Run drift and delayed-feedback jobs
7. Review the manual retraining signal
```
