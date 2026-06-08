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
- `/models:/uplift_model@champion`
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

- delayed feedback simulation
- observed outcome
- realized value

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