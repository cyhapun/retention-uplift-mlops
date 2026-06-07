from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_POLICY_CONFIG_PATH = Path("src/policy/policy_config.yaml")


@dataclass(frozen=True)
class ActionConfig:
    name: str
    cost: float
    min_expected_value: float
    min_uplift: float
    priority: int


@dataclass(frozen=True)
class PolicyConfig:
    actions: dict[str, ActionConfig]
    min_uplift_for_action: float
    max_daily_budget: float


def load_policy_config(path: str | Path = DEFAULT_POLICY_CONFIG_PATH) -> PolicyConfig:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Policy config not found at {path}")

    raw_config = yaml.safe_load(path.read_text(encoding="utf-8"))

    actions = {
        action_name: ActionConfig(
            name=action_name,
            cost=float(action_values["cost"]),
            min_expected_value=float(action_values["min_expected_value"]),
            min_uplift=float(action_values.get("min_uplift", 0.0)),
            priority=int(action_values.get("priority", 0)),
        )
        for action_name, action_values in raw_config["actions"].items()
    }

    thresholds = raw_config.get("thresholds", {})

    return PolicyConfig(
        actions=actions,
        min_uplift_for_action=float(thresholds.get("min_uplift_for_action", 0.0)),
        max_daily_budget=float(thresholds.get("max_daily_budget", 0.0)),
    )
