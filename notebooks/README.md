# Notebooks

These notebooks provide visual walkthroughs for RetentionOps.

Production logic should stay in `src/`.

The notebooks should:

- explain each modeling step
- call reusable functions from `src/`
- display dataset summaries
- visualize model outputs
- link results back to MLflow, reports, and artifacts

## Notebooks

| Notebook | Purpose |
|---|---|
| `01_data_exploration.ipynb` | EDA and problem framing |
| `03_response_model_training.ipynb` | Baseline response model training walkthrough |
| `04_uplift_model_training.ipynb` | T-Learner uplift model training walkthrough |

## Setup

```powershell
pip install -r requirements-dev.txt
python -m ipykernel install --user --name retention-uplift-mlops
jupyter lab

## Rules

- Do not duplicate production training logic in notebooks.
- Use notebooks as orchestration, explanation, and visualization layers.