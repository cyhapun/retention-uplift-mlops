# Modeling Notes

## Response Model

The response model predicts:

```text
P(conversion | features)
```

It is useful as a baseline but insufficient for treatment decisioning.

A user with high conversion probability may convert even without intervention.

## Uplift Model

The T-Learner estimates:

```text
P(conversion | treatment = 1, features)
-
P(conversion | treatment = 0, features)
```

The model trains two separate outcome models:

- `treatment_model`
- `control_model`

At prediction time:

```python
treatment_probability = treatment_model.predict_proba(features)
control_probability = control_model.predict_proba(features)
uplift_score = treatment_probability - control_probability
```

## Why Treatment and Control Matter

Uplift modeling requires both treatment and control groups.

If the dataset contains only treatment users, the model cannot estimate the counterfactual control outcome.

## Evaluation

The project uses:

- ROC-AUC
- PR-AUC
- Log loss
- uplift decile report
- Qini-style curve
- Qini/AUUC-style summary

Standard classification metrics are useful for outcome models, but uplift models also require ranking and treatment-effect diagnostics.

## Policy Connection

The model output is not the final decision.

The policy engine combines:

- `uplift_score`
- `customer_value`
- `treatment_cost`

to produce:

- `expected_incremental_value`
- `recommended_action`