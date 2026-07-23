# Project Summary

## Project Name

RetentionOps: Uplift Modeling and MLOps for Retention Decisioning

## Problem

Traditional churn or conversion models predict whether a user is likely to convert or churn. However, they do not answer the more important business question:

```text
Will an intervention actually change this user's behavior?
```

RetentionOps uses uplift modeling to estimate the incremental effect of treatment.

## Core Idea

A response model predicts:

```text
P(conversion | features)
```

An uplift model predicts:

```text
P(conversion | treatment = 1, features)
-
P(conversion | treatment = 0, features)
```

This allows the system to target users based on incremental impact rather than raw conversion probability.

## Dataset

The project uses the Criteo Uplift dataset.

Important data pipeline lesson:

> The raw dataset can be ordered by treatment assignment.
> 
> Therefore, the pipeline samples across the full raw file instead of reading only the first N rows.

## Modeling

The project includes:

| Model | Purpose |
|-------|---------|
| Logistic Regression | Simple response baseline |
| Random Forest | Non-linear response baseline |
| XGBoost response model | Strong tabular response baseline |
| T-Learner XGBoost uplift model | Estimate treatment effect |

## Decisioning

The policy engine converts uplift score into expected incremental value:

```text
expected_incremental_value = uplift_score * customer_value - treatment_cost
```

Actions:

- `no_action`
- `low_cost_email`
- `standard_discount`
- `premium_offer`

## MLOps Capabilities

RetentionOps includes:

- MLflow tracking
- MLflow model registry
- FastAPI model serving
- PostgreSQL decision logging
- Delayed feedback simulation
- Prometheus metrics
- Grafana dashboard
- Evidently drift detection
- Docker Compose stack
- GitHub Actions CI

## What Makes This Project Different

This is not a standard churn prediction project.

It demonstrates:

- causal-style treatment effect thinking
- business-aware decisioning
- model registry usage
- service observability
- decision audit trail
- feedback simulation
- drift monitoring
- production-like Docker workflow

## End-to-End Lifecycle

```text
data ingestion
→ validation and dataset creation
→ EDA and baseline model
→ T-Learner uplift model
→ evaluation and model registry
→ API serving and policy decision
→ PostgreSQL decision logging
→ monitoring and drift detection
→ delayed feedback simulation
→ manual retraining signal
→ CI/CD
```

## Quick Run

```powershell
Copy-Item .env.example .env
docker compose build
.\scripts\docker-bootstrap.ps1 -BuildData -Train -Monitoring
.\scripts\docker-smoke-test.ps1
```

The raw file must exist at `data/raw/criteo-uplift.csv` before using `-BuildData`. If processed datasets and a registered model already exist, use `-Train -Monitoring` instead.

## Main Outputs

- `data/processed/train.parquet`, `valid.parquet`, `test.parquet`
- `data/reference/reference.parquet`
- `artifacts/uplift/treatment_model.pkl`
- `artifacts/uplift/control_model.pkl`
- `reports/uplift/uplift_decile_report.csv`
- `reports/uplift/qini_curve.csv`
- `reports/drift/*`
- MLflow registered model `uplift_model@champion`

## Portfolio Talking Point

This project shows how to move from a machine learning notebook to an end-to-end MLOps decision system.
