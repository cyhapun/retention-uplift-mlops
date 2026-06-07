# RetentionOps

RetentionOps is an end-to-end uplift modeling and MLOps project for customer retention decisioning.

## Problem Statement

Traditional churn models estimate which users are likely to churn or convert. However, high risk does not always mean high treatment value.

This project focuses on uplift modeling:

> The best customers to target are those whose behavior changes because of the intervention.

## Project Goal

Given user features, the system will:

1. Predict the outcome under treatment.
2. Predict the outcome under control.
3. Estimate uplift.
4. Calculate expected incremental value.
5. Recommend the best business action.
6. Serve decisions through a FastAPI service.
7. Log decisions for monitoring, audit, feedback, and retraining.

## Dataset

This project uses the Criteo Uplift Prediction Dataset, which contains treatment/control assignment and outcome labels suitable for uplift modeling.

Expected columns:

- `f0` to `f10`: user features
- `treatment`: treatment/control flag
- `conversion`: main target
- `visit`: optional target for MVP if conversion is too sparse

## Architecture

```text
Raw Data
  -> Data Processing
  -> EDA
  -> Baseline Response Model
  -> T-Learner Uplift Model
  -> Business Policy Engine
  -> MLflow Registry
  -> FastAPI Decision Service
  -> PostgreSQL Decision Logs
  -> Prometheus + Grafana Monitoring
  -> Evidently Drift Detection
  -> Feedback Simulation
  -> Retraining Trigger
```

## Project Structure

```text
retentionops/
├── data/
├── notebooks/
├── src/
│   ├── data/
│   ├── features/
│   ├── models/
│   ├── policy/
│   ├── serving/
│   ├── monitoring/
│   └── db/
├── tests/
├── docker/
├── grafana/
├── reports/
├── artifacts/
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── README.md
```

## Setup

Create virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
make install
```

Run tests:

```bash
make test
```

Run lint:

```bash
make lint
```
