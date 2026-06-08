# Project Summary

## Project Name

RetentionOps: Uplift Modeling and MLOps for Retention Decisioning

## Problem

Traditional churn or conversion models predict whether a user is likely to convert or churn. However, they do not answer the more important business question:

```text
Will an intervention actually change this user's behavior?

RetentionOps uses uplift modeling to estimate the incremental effect of treatment.

Core Idea

A response model predicts:

P(conversion | features)

An uplift model predicts:

P(conversion | treatment = 1, features)
-
P(conversion | treatment = 0, features)

This allows the system to target users based on incremental impact rather than raw conversion probability.

Dataset

The project uses the Criteo Uplift dataset.

Important data pipeline lesson:

The raw dataset can be ordered by treatment assignment.

Therefore, the pipeline samples across the full raw file instead of reading only the first N rows.

Modeling

The project includes:

Model	Purpose
Logistic Regression	Simple response baseline
Random Forest	Non-linear response baseline
XGBoost response model	Strong tabular response baseline
T-Learner XGBoost uplift model	Estimate treatment effect
Decisioning

The policy engine converts uplift score into expected incremental value:

expected_incremental_value = uplift_score * customer_value - treatment_cost

Actions:

no_action
low_cost_email
standard_discount
premium_offer
MLOps Capabilities

RetentionOps includes:

MLflow tracking
MLflow model registry
FastAPI model serving
PostgreSQL decision logging
Delayed feedback simulation
Prometheus metrics
Grafana dashboard
Evidently drift detection
Docker Compose stack
GitHub Actions CI
What Makes This Project Different

This is not a standard churn prediction project.

It demonstrates:

causal-style treatment effect thinking
business-aware decisioning
model registry usage
service observability
decision audit trail
feedback simulation
drift monitoring
production-like Docker workflow
End-to-End Lifecycle
data ingestion
→ validation
→ EDA
→ baseline model
→ uplift model
→ model registry
→ API serving
→ policy decision
→ logging
→ monitoring
→ drift detection
→ feedback simulation
→ CI/CD
Portfolio Talking Point

This project shows how to move from a machine learning notebook to an end-to-end MLOps decision system.