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

## Phase 1: Data Ingestion and Sampling

The raw Criteo uplift dataset should be placed at:

```text
data/raw/criteo-uplift.csv
```

To build a small development dataset:

```bash
make data-sample
```

To build a larger MVP dataset:

```bash
make data
```

Generated files:

```text
data/interim/sample_100k.parquet
data/interim/sample_1m.parquet
data/processed/train.parquet
data/processed/valid.parquet
data/processed/test.parquet
data/processed/dataset_summary.parquet
data/reference/reference.parquet
```

The reference dataset will be used later for drift detection.

### Important sampling note

The raw Criteo uplift CSV can be ordered by treatment assignment. Therefore, the data pipeline must not read only the first N rows.

Instead, RetentionOps samples rows across the full raw CSV using chunked reading. This ensures that the generated train, validation, and test datasets contain both treatment and control groups.

## Phase 2: EDA and Problem Framing

The processed training dataset is explored in:

```text
notebooks/01_data_exploration.ipynb
```

### Key EDA Findings

1. **Treatment vs. Control Distribution**:
   - The training dataset is correctly balanced for uplift modeling, containing both groups: **~85% Treatment** and **~15% Control**.
   - Feature distributions between treatment and control groups are almost identical, confirming a valid Randomized Controlled Trial (RCT) setup without sampling bias.

2. **Target Class Imbalance**:
   - The primary target (`conversion`) is extremely imbalanced, with a positive conversion rate of only **~0.29%**.
   - **Action**: Standard metrics like Accuracy are not applicable. We must use uplift-specific metrics such as **AUUC (Area Under Uplift Curve)** and **Qini Curve**. Stratified sampling is also crucial during validation splits.

3. **Observed Uplift**:
   - Treatment Conversion Rate: **~0.307%**
   - Control Conversion Rate: **~0.182%**
   - **Absolute Uplift**: **+0.125%**
   - **Action**: The treatment shows a clear positive effect. Uplift modeling is feasible and can help identify the persuable segment.

4. **Feature Characteristics**:
   - Features exhibit significant **skewness** (e.g., `f1`, `f4`, `f5` have extreme skew) and contain outliers.
   - Moderate to strong **multicollinearity** exists between certain feature pairs (e.g., `f5` and `f7`).
   - **Action**: **Tree-based models** (like XGBoost, LightGBM) are highly recommended as they naturally handle multicollinearity, non-linear relationships, and skewed features without requiring extensive scaling or transformations.