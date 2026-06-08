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

## Phase 3: Baseline Response Model

This phase trains standard binary classification models to predict:

```text
P(conversion | features)
```

This is not an uplift model yet. It is a baseline response model used for comparison before training the T-Learner uplift model.

### Models

Logistic Regression
Random Forest
XGBoost

### Metrics

ROC-AUC
PR-AUC
Log loss

Because the target can be highly imbalanced, PR-AUC is used as the main model selection metric.

### Run MLflow UI

```text
mlflow ui --host 0.0.0.0 --port 5000
```

Open:

```text
http://localhost:5000
```

### Train response models

```text
make train-response
```

Or:

```text
python -m src.models.train_response_model
```

### Output

The best baseline response model is saved locally to:

```text
artifacts/response_model.pkl
```

MLflow logs each candidate model with params, metrics, and model artifacts under the response_model experiment.

## Phase 4: T-Learner Uplift Model

This phase trains a T-Learner uplift model to estimate the incremental effect of treatment.

The uplift score is defined as:

```text
uplift_score = P(conversion | treatment = 1, features) - P(conversion | treatment = 0, features)
```

### Why this matters
The baseline response model from Phase 3 predicts:

```text
P(conversion | features)
```

That is useful, but not enough for treatment decisioning.

A user with high conversion probability may convert even without an intervention. The uplift model estimates whether the intervention changes the user's behavior.

### T-Learner approach

The T-Learner trains two separate outcome models:

```text
treatment_model: trained on treatment = 1 users
control_model: trained on treatment = 0 users
```

At prediction time:

```text
treatment_probability = treatment_model.predict_proba(features)
control_probability = control_model.predict_proba(features)
uplift_score = treatment_probability - control_probability
```

### Run training

Start MLflow UI:

```text
mlflow ui --host 0.0.0.0 --port 5000
```

Train uplift model:
   
```text
make train-uplift
```

Or:

```text
python -m src.models.train_uplift_model
```

### Outputs

Local generated artifacts:

```text
artifacts/uplift/treatment_model.pkl
artifacts/uplift/control_model.pkl
reports/uplift/valid_uplift_predictions.parquet
reports/uplift/uplift_decile_report.csv
reports/uplift/qini_curve.csv
```

MLflow experiment:

```text
uplift_model
```

Logged metrics include:

```text
treatment_model_roc_auc
treatment_model_pr_auc
treatment_model_log_loss
control_model_roc_auc
control_model_pr_auc
control_model_log_loss
mean_predicted_uplift
share_positive_uplift
qini_auc
incremental_qini_auc
top_decile_observed_uplift
```

### Evaluation note

Uplift models cannot be evaluated only with standard classification metrics because each user has only one observed outcome. Therefore, this phase also uses uplift-specific diagnostics:

```text
uplift by decile
observed uplift by bucket
Qini curve
Qini/AUUC-style area metrics
```

## Phase 5: Business Policy Engine

This phase converts uplift predictions into business decisions.

The uplift model from Phase 4 estimates:

```text
uplift_score = P(conversion | treatment = 1, features) - P(conversion | treatment = 0, features)
```

The policy engine converts this score into expected incremental value:

```text
expected_incremental_value = uplift_score * customer_value - treatment_cost
```

Actions

The current policy supports:

```text
Action	Cost	Purpose
no_action	0.0	Do not intervene
low_cost_email	0.2	Low-cost intervention
standard_discount	5.0	Medium-cost offer
premium_offer	15.0	High-value intervention
```

Policy config

Policy rules are configured in:

```text
src/policy/policy_config.yaml
```

Run policy tests:

```text
make test-policy
```

Or:

```text
pytest tests/test_policy.py tests/test_budget_optimizer.py -q
```

Example
```text
from src.policy.decision_engine import recommend_action_from_policy

decision = recommend_action_from_policy(
    uplift_score=0.12,
    customer_value=100,
)

print(decision)
```
Example output:

```text
recommended_action: standard_discount
expected_incremental_value: 7.0
treatment_cost: 5.0
```

Why this matters

A model score alone is not a business decision. The policy engine makes the project production-oriented by separating:

ML prediction logic
```text
from
business decision logic
```

This makes the system easier to test, audit, tune, and serve through the FastAPI service in later phases.

## Phase 6: MLflow Model Registry

This phase registers the T-Learner uplift model as a single MLflow PyFunc model.

The registered model wraps two artifacts:

```text
treatment_model.pkl
control_model.pkl
```

At prediction time, the wrapper returns:

```text
treatment_probability
control_probability
uplift_score
```

### Why Model Registry?

Previous phases loaded models from local pickle paths. This is not ideal for production because API code would depend on hard-coded local files.

With MLflow Model Registry, the serving layer can load:

models:/uplift_model@champion

The champion alias points to the model version currently approved for serving.

Start MLflow

For local development with registry support:

mlflow ui --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5000

Then set:

```bash
$env:MLFLOW_TRACKING_URI="http://localhost:5000"
```

Register uplift model

```bash
make register-uplift
```

Or:

```bash
python -m src.models.register_uplift_model
```

Test loading by alias

```bash
make test-registry
```

Or:
```bash
python -c "import pandas as pd; from src.data.constants import FEATURE_COLS; from src.serving.model_loader import load_uplift_model; model=load_uplift_model(); X=pd.DataFrame([{f:0.0 for f in FEATURE_COLS}]); print(model.predict(X))"
```

### Files

```text
src/models/uplift_wrapper.py
src/models/register_uplift_model.py
src/serving/model_loader.py
```

### Expected registered model

```text
Name: uplift_model
Alias: champion
URI: models:/uplift_model@champion
```

## Phase 7: FastAPI Decision Service

This phase exposes the uplift model and policy engine through a REST API.

The API flow is:

```text
Request features
→ Load uplift model from MLflow Registry
→ Predict treatment probability
→ Predict control probability
→ Calculate uplift score
→ Apply business policy
→ Return recommended action
```

### Start MLflow

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5000
```

### Set tracking URI

```bash
$env:MLFLOW_TRACKING_URI="http://localhost:5000"
```

### Run API

```bash
make api
```

Or:

```bash
uvicorn src.serving.main:app --host 0.0.0.0 --port 8000 --reload
```

### Open Swagger UI

```text
http://localhost:8000/docs
```

### Open ReDoc

```text
http://localhost:8000/redoc
```

### Endpoints

http://localhost:8000/redoc

```text
Endpoints
Method	Endpoint	Purpose
GET	/health	Health check
GET	/model-info	Current model name, alias, and URI
POST	/decide-action	Predict uplift and recommend action
```

### Example request

```text
{
  "user_id": "user_001",
  "customer_value": 100,
  "features": {
    "f0": 0.0,
    "f1": 0.0,
    "f2": 0.0,
    "f3": 0.0,
    "f4": 0.0,
    "f5": 0.0,
    "f6": 0.0,
    "f7": 0.0,
    "f8": 0.0,
    "f9": 0.0,
    "f10": 0.0
  }
}
```

### Example response

```text
{
  "user_id": "user_001",
  "treatment_probability": 0.25,
  "control_probability": 0.10,
  "uplift_score": 0.15,
  "customer_value": 100.0,
  "treatment_cost": 5.0,
  "expected_incremental_value": 10.0,
  "roi": 2.0,
  "recommended_action": "standard_discount",
  "decision_reason": [
    "positive_uplift",
    "positive_expected_value",
    "action_threshold_met"
  ],
  "model_name": "uplift_model",
  "model_alias": "champion",
  "model_version": "..."
}
```

### Test API

```bash
make test-api
```

Or:

```bash
pytest tests/test_api.py tests/test_schemas.py -q
```