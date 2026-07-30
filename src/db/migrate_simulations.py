"""Initialize simulation metadata and verify temporary artifact cleanup."""

from src.db.database import init_database
from src.ops.simulation_service import SimulationService


def main() -> None:
    init_database()
    service = SimulationService()
    try:
        service.initialize()
        print(
            "Simulation metadata initialized; "
            f"removed {service.cleanup_expired()} expired artifact set(s)."
        )
        print(f"Artifact root: {service.config.artifact_root}")
    finally:
        service.shutdown()


if __name__ == "__main__":
    main()
