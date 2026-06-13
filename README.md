# RetentionOps: Uplift Modeling MLOps System

RetentionOps is an end-to-end MLOps project for retention decisioning with uplift modeling.

Instead of asking:

> Who is likely to convert?

this project asks:

> Who is likely to change behavior because of an intervention?

The system estimates uplift, applies a business policy, serves decisions through FastAPI, logs decisions to PostgreSQL, monitors the API with Prometheus/Grafana, detects drift with Evidently, and simulates delayed feedback for future retraining.

## Architecture

See: [docs/architecture.md](docs/architecture.md)

## Key Features

- Full-file data sampling to preserve treatment/control groups
- EDA and problem framing for uplift modeling
- Baseline response models
- T-Learner uplift model
- MLflow experiment tracking and model registry
- FastAPI decision service
- Config-driven business policy engine
- PostgreSQL decision logging
- Delayed feedback simulation
- Prometheus and Grafana monitoring
- Evidently drift detection
- Docker Compose full local stack
- GitHub Actions CI/CD

## Quick Start

```powershell
Copy-Item .env.example .env
docker compose build
.\scripts\docker-bootstrap.ps1 -Train -Monitoring
.\scripts\docker-smoke-test.ps1
```

## URLs

| Service | URL |
|---------|-----|
| MLflow | http://localhost:5000 |
| FastAPI docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Grafana login:

- `admin` / `admin`

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | System architecture |
| [docs/demo.md](docs/demo.md) | End-to-end demo |
| [docs/api_examples.md](docs/api_examples.md) | API request examples |
| [docs/modeling_notes.md](docs/modeling_notes.md) | Modeling explanation |
| [docs/mlops_lifecycle.md](docs/mlops_lifecycle.md) | MLOps lifecycle |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues and fixes |
| [docs/project_summary.md](docs/project_summary.md) | Portfolio summary |

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

## Local Development Setup

Create virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
make install
```

Run tests and linting:

```bash
make test
make lint
```

## System Components & Workflow

<details>
<summary><b>Data Ingestion and Sampling</b></summary>

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

</details>

<details>
<summary><b>Exploratory Data Analysis (EDA)</b></summary>

The processed training dataset is explored in:

```text
notebooks/eda.ipynb
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

</details>

<details>
<summary><b>Baseline Response Model</b></summary>

Standard binary classification models are trained to predict:

```text
P(conversion | features)
```

This is not an uplift model yet. It is a baseline response model used for comparison before training the T-Learner uplift model.

### Models

- Logistic Regression
- Random Forest
- XGBoost

### Metrics

- ROC-AUC
- PR-AUC
- Log loss

Because the target can be highly imbalanced, PR-AUC is used as the main model selection metric.

### Run MLflow UI

```bash
mlflow ui --host 0.0.0.0 --port 5000
```

Open: `http://localhost:5000`

### Train response models

```bash
make train-response
```

Or:

```bash
python -m src.models.train_response_model
```

### Output

The best baseline response model is saved locally to:

```text
artifacts/response_model.pkl
```

MLflow logs each candidate model with params, metrics, and model artifacts under the `response_model` experiment.

</details>

<details>
<summary><b>T-Learner Uplift Model</b></summary>

A T-Learner uplift model is trained to estimate the incremental effect of treatment.

The uplift score is defined as:

```text
uplift_score = P(conversion | treatment = 1, features) - P(conversion | treatment = 0, features)
```

### Why this matters

The baseline response model predicts:

```text
P(conversion | features)
```

That is useful, but not enough for treatment decisioning.

A user with high conversion probability may convert even without an intervention. The uplift model estimates whether the intervention changes the user's behavior.

### T-Learner approach

The T-Learner trains two separate outcome models:

- `treatment_model`: trained on treatment = 1 users
- `control_model`: trained on treatment = 0 users

At prediction time:

```python
treatment_probability = treatment_model.predict_proba(features)
control_probability = control_model.predict_proba(features)
uplift_score = treatment_probability - control_probability
```

### Run training

Start MLflow UI:

```bash
mlflow ui --host 0.0.0.0 --port 5000
```

Train uplift model:
   
```bash
make train-uplift
```

Or:

```bash
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

MLflow experiment: `uplift_model`

Logged metrics include:

- `treatment_model_roc_auc`
- `treatment_model_pr_auc`
- `treatment_model_log_loss`
- `control_model_roc_auc`
- `control_model_pr_auc`
- `control_model_log_loss`
- `mean_predicted_uplift`
- `share_positive_uplift`
- `qini_auc`
- `incremental_qini_auc`
- `top_decile_observed_uplift`

### Evaluation note

Uplift models cannot be evaluated only with standard classification metrics because each user has only one observed outcome. Therefore, uplift-specific diagnostics are also used:

- uplift by decile
- observed uplift by bucket
- Qini curve
- Qini/AUUC-style area metrics

</details>

<details>
<summary><b>Business Policy Engine</b></summary>

The policy engine converts uplift predictions into business decisions.

The uplift model estimates:

```text
uplift_score = P(conversion | treatment = 1, features) - P(conversion | treatment = 0, features)
```

The policy engine converts this score into expected incremental value:

```text
expected_incremental_value = uplift_score * customer_value - treatment_cost
```

### Actions

The current policy supports:

| Action | Cost | Purpose |
|--------|------|---------|
| `no_action` | 0.0 | Do not intervene |
| `low_cost_email` | 0.2 | Low-cost intervention |
| `standard_discount` | 5.0 | Medium-cost offer |
| `premium_offer` | 15.0 | High-value intervention |

### Policy config

Policy rules are configured in: `src/policy/policy_config.yaml`

Run policy tests:

```bash
make test-policy
```

Or:

```bash
pytest tests/test_policy.py tests/test_budget_optimizer.py -q
```

### Example

```python
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

### Why this matters

A model score alone is not a business decision. The policy engine makes the project production-oriented by separating ML prediction logic from business decision logic.

This makes the system easier to test, audit, tune, and serve through the FastAPI service.

</details>

<details>
<summary><b>MLflow Model Registry</b></summary>

The T-Learner uplift model is registered as a single MLflow PyFunc model.

The registered model wraps two artifacts:

- `treatment_model.pkl`
- `control_model.pkl`

At prediction time, the wrapper returns:

- `treatment_probability`
- `control_probability`
- `uplift_score`

### Why Model Registry?

During experimentation, models are loaded from local pickle paths. This is not ideal for production because API code would depend on hard-coded local files.

With MLflow Model Registry, the serving layer can load:

```text
models:/uplift_model@champion
```

The `champion` alias points to the model version currently approved for serving.

### Start MLflow

For local development with registry support:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5000
```

Then set:

```powershell
$env:MLFLOW_TRACKING_URI="http://localhost:5000"
```

### Register uplift model

```bash
make register-uplift
```

Or:

```bash
python -m src.models.register_uplift_model
```

### Test loading by alias

```bash
make test-registry
```

Or:

```bash
python -c "import pandas as pd; from src.data.constants import FEATURE_COLS; from src.serving.model_loader import load_uplift_model; model=load_uplift_model(); X=pd.DataFrame([{f:0.0 for f in FEATURE_COLS}]); print(model.predict(X))"
```

### Files

- `src/models/uplift_wrapper.py`
- `src/models/register_uplift_model.py`
- `src/serving/model_loader.py`

### Expected registered model

```text
Name: uplift_model
Alias: champion
URI: models:/uplift_model@champion
```

</details>

<details>
<summary><b>FastAPI Decision Service</b></summary>

The FastAPI service exposes the uplift model and policy engine through a REST API.

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

### Start MLflow & Set tracking URI

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5000
```

```powershell
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

### Endpoints & Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | Health check |
| `GET` | `/model-info` | Current model name, alias, and URI |
| `POST` | `/decide-action` | Predict uplift and recommend action |

### Example request & response

**Request**:

```json
{
  "user_id": "user_001",
  "customer_value": 100,
  "features": {
    "f0": 0.0, "f1": 0.0, "f2": 0.0, "f3": 0.0, "f4": 0.0,
    "f5": 0.0, "f6": 0.0, "f7": 0.0, "f8": 0.0, "f9": 0.0, "f10": 0.0
  }
}
```

**Response**:

```json
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

### Docker Development Workflow

To avoid running MLflow, model registration, and FastAPI manually in multiple terminals, use the Docker Compose dev stack.

| Service | Purpose |
|---------|---------|
| `mlflow` | MLflow Tracking and Model Registry |
| `api` | FastAPI decision service |
| `jobs` | One-off commands for training, registration, and tests |

If processed data already exists:

```powershell
.\scripts\docker-dev.ps1 -Train
```

If data also needs to be generated:

```powershell
.\scripts\docker-dev.ps1 -BuildData -Train
```

Regular run:

```bash
docker compose up -d mlflow api
```

Useful commands:

```bash
docker compose logs -f
docker compose logs -f api
docker compose logs -f mlflow
docker compose down
```

</details>

<details>
<summary><b>PostgreSQL Decision Logging</b></summary>

Each API decision is logged to PostgreSQL.

When `/decide-action` is called, the API stores:
`decision_id`, `user_id`, `features`, `treatment_probability`, `control_probability`, `uplift_score`, `customer_value`, `treatment_cost`, `expected_incremental_value`, `roi`, `recommended_action`, `decision_reason`, `model_name`, `model_alias`, `model_version`, `created_at`.

### Start services

```bash
docker compose up -d postgres mlflow
```

### Initialize database

```bash
docker compose run --rm jobs python -m src.db.init_db
```

### Start API

```bash
docker compose up -d api
```

### Query decision logs

```bash
docker compose exec postgres psql -U retentionops -d retentionops
```

```sql
SELECT COUNT(*) FROM decision_logs;

SELECT
  decision_id,
  user_id,
  uplift_score,
  expected_incremental_value,
  recommended_action,
  created_at
FROM decision_logs
ORDER BY created_at DESC
LIMIT 5;

SELECT recommended_action, COUNT(*)
FROM decision_logs
GROUP BY recommended_action
ORDER BY COUNT(*) DESC;
```

### Why this matters

Decision logging makes the system auditable and production-oriented.

The logs will be used later for:
- monitoring action distribution
- tracking average uplift score
- simulating delayed feedback
- evaluating model decisions
- triggering retraining

</details>

<details>
<summary><b>Prometheus Metrics and Grafana Dashboard</b></summary>

Monitoring is added for the FastAPI decision service.

The API exposes Prometheus metrics at `/metrics`.

| Metric | Purpose |
|--------|---------|
| `retentionops_api_requests_total` | API request count |
| `retentionops_api_errors_total` | API error count |
| `retentionops_api_latency_seconds` | API latency histogram |
| `retentionops_recommended_action_total` | Recommended action distribution |
| `retentionops_uplift_score` | Uplift score distribution |
| `retentionops_expected_incremental_value` | Expected value distribution |

### Start monitoring stack

```bash
docker compose up -d postgres mlflow api prometheus grafana
```

### URLs

- FastAPI docs: `http://localhost:8000/docs`
- Metrics: `http://localhost:8000/metrics`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (Login: `admin` / `admin`)

### Prometheus target

In Prometheus (`Status → Targets`), you should see: `retentionops-api UP`

### Grafana dashboard

Dashboard path: `Dashboards → RetentionOps → RetentionOps Monitoring`

Panels include: API Requests per Second, API p95 Latency, API Error Rate, Recommended Action Distribution, Average Uplift Score, Average Expected Incremental Value.

### Generate traffic

```powershell
1..20 | ForEach-Object {
  Invoke-RestMethod `
    -Uri "http://localhost:8000/decide-action" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
}
```

### Why this matters

Monitoring makes the decision service observable. It helps answer:
- Is the API healthy?
- Is latency increasing?
- Are errors happening?
- Which actions are being recommended most often?
- Is uplift score distribution changing?
- Is expected value still positive?

</details>

<details>
<summary><b>Drift Detection with Evidently</b></summary>

Reference data is compared against current or simulated production data to detect data drift.

- Reference data: `data/reference/reference.parquet`
- Current data: `data/processed/test.parquet`
- Simulated drifted data: `data/processed/test_drifted.parquet`

### Run drift reports

Run normal drift report:

```bash
docker compose run --rm jobs python -m src.monitoring.drift_report --current-path data/processed/test.parquet --report-name data_drift_report
```

Create simulated drift:

```bash
docker compose run --rm jobs python -m src.monitoring.simulate_drift
```

Run drifted report:

```bash
docker compose run --rm jobs python -m src.monitoring.drift_report --current-path data/processed/test_drifted.parquet --report-name data_drift_report_drifted
```

### Outputs

```text
reports/drift/data_drift_report_summary.json
reports/drift/data_drift_report_features.csv
reports/drift/data_drift_report_drifted_summary.json
reports/drift/data_drift_report_drifted_features.csv
```

If supported by the installed Evidently version, HTML reports are also generated:

```text
reports/drift/data_drift_report.html
reports/drift/data_drift_report_drifted.html
```

### Why this matters

Drift detection helps answer:
- Is production data still similar to training/reference data?
- Are important features shifting?
- Should we investigate or retrain the model?

This process produces a retraining signal:

```json
{
  "should_retrain": true,
  "retrain_reasons": ["..."]
}
```

</details>

<details>
<summary><b>Delayed Feedback Simulation</b></summary>

Delayed feedback is simulated for API decisions.

The API stores decisions in `decision_logs`.
The feedback simulation creates observed outcomes in `feedback_logs`.

### Feedback logic

For each decision without feedback:

```python
if recommended_action != 'no_action':
    outcome_probability = treatment_probability
else:
    outcome_probability = control_probability
```

Then the simulator samples: `observed_outcome ~ Bernoulli(outcome_probability)`
And calculates: `realized_value = observed_outcome * customer_value - treatment_cost`

### Run feedback simulation

```bash
docker compose run --rm jobs python -m src.feedback.simulate_feedback --limit 1000 --feedback-delay-days 7
```

Or:

```bash
make docker-simulate-feedback
```

### Query feedback logs

```bash
docker compose exec postgres psql -U retentionops -d retentionops
```

```sql
SELECT COUNT(*) FROM feedback_logs;

SELECT
  d.user_id,
  d.recommended_action,
  d.uplift_score,
  d.expected_incremental_value,
  f.observed_outcome,
  f.realized_value
FROM feedback_logs f
JOIN decision_logs d
  ON d.decision_id = f.decision_id
ORDER BY f.created_at DESC
LIMIT 10;
```

### Why this matters

Delayed feedback closes the decision loop.
It helps answer:
- Which decisions eventually converted?
- Which actions created realized value?
- How does expected value compare with simulated realized value?
- Which logged decisions can be used for future retraining?

This prepares the project for retraining and model lifecycle automation.

</details>

<details>
<summary><b>Full Docker Compose Stack</b></summary>

The local Docker Compose stack provides a complete environment for RetentionOps.

### Services

| Service | URL | Purpose |
|---------|-----|---------|
| PostgreSQL | `localhost:5432` | Decision and feedback logs |
| MLflow | `http://localhost:5000` | Tracking and Model Registry |
| FastAPI | `http://localhost:8000/docs` | Decision API |
| Prometheus | `http://localhost:9090` | Metrics scraping |
| Grafana | `http://localhost:3000` | Monitoring dashboard |
| Jobs | n/a | One-off training, registration, drift, feedback jobs |

### First-time setup

Create local environment file:

```powershell
Copy-Item .env.example .env
```

Build images:

```powershell
docker compose build
```

If processed data already exists:

```powershell
.\scripts\docker-bootstrap.ps1 -Train -Monitoring
```

If processed data needs to be generated:

```powershell
.\scripts\docker-bootstrap.ps1 -BuildData -Train -Monitoring
```

### Regular startup

If model has already been trained and registered:

```powershell
docker compose up -d postgres mlflow api prometheus grafana
```

### Smoke test

```powershell
.\scripts\docker-smoke-test.ps1
```

### Useful commands

```powershell
docker compose ps
docker compose logs -f
docker compose logs -f api
docker compose logs -f mlflow
docker compose down
docker compose down -v
```

### Important note

When using Docker, train and register the uplift model inside the jobs container:

```powershell
docker compose run --rm jobs python -m src.models.train_uplift_model
docker compose run --rm jobs python -m src.models.register_uplift_model
```

This keeps MLflow artifact paths consistent across containers.

Generated runtime files are not committed:

```text
mlflow.db
mlruns/
artifacts/
reports/
data/processed/
Docker volumes
```

</details>

<details>
<summary><b>GitHub Actions CI/CD</b></summary>

Automated validation is performed with GitHub Actions.

### Workflows

| Workflow | File | Purpose |
|----------|------|---------|
| Python CI | `.github/workflows/ci.yml` | Run lint, format check, and tests |
| Docker CI | `.github/workflows/docker.yml` | Validate Docker Compose, build images, and run tests in container |

### Python CI checks

```bash
ruff check src tests
ruff format src tests --check
pytest tests -q
```

### Docker CI checks

```bash
docker compose config
docker compose build api jobs
docker compose run --rm --no-deps jobs pytest tests -q
```

### Run CI locally

```bash
make ci
make ci-docker
```

### Pull request workflow

Every PR should pass: Python CI and Docker CI before merge.

### Why Docker CI does not start the full stack

The full stack requires a trained and registered MLflow model (`models:/uplift_model@champion`).

Model artifacts are generated runtime files and are not committed. Therefore, Docker CI validates image build and containerized tests, while full end-to-end stack validation remains a local smoke test:

```powershell
.\scripts\docker-bootstrap.ps1 -Train -Monitoring
.\scripts\docker-smoke-test.ps1
```

</details>

<details>
<summary><b>Visual Model Training Notebooks</b></summary>

Production training code lives under:

```text
src/models/
```

The notebooks are visual walkthroughs. They explain and execute the training workflow by importing reusable code from `src/`.

| Notebook | Purpose |
|---|---|
| `notebooks/03_response_model_training.ipynb` | Train and inspect baseline response models |
| `notebooks/04_uplift_model_training.ipynb` | Train and inspect T-Learner uplift model |

### Setup

```bash
pip install -r requirements-dev.txt
python -m ipykernel install --user --name retention-uplift-mlops
jupyter lab
```

### Regenerate notebooks

```bash
python scripts/create_training_notebooks.py
```

Or:

```bash
make create-training-notebooks
```

### Design rule

Docker and CI continue to run Python scripts from `src/`.

Notebooks are not production entrypoints. They are used for:

- explanation
- visual inspection
- plots
- model training walkthroughs
- portfolio demo

This keeps the project reproducible while making the modeling workflow easier to understand.

</details>
