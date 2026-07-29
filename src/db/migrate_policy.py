"""Create additive policy tables and seed the active version from YAML."""

from src.db.database import init_database
from src.policy.store import ensure_policy_seed


def main() -> None:
    init_database()
    ensure_policy_seed()
    print("Policy tables initialized and the active policy seed verified.")


if __name__ == "__main__":
    main()
