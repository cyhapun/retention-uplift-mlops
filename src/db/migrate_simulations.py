"""Initialize simulation metadata and verify temporary artifact cleanup."""

from src.db.database import init_database
from src.ops.simulation_prediction_service import SimulationPredictionService
from src.ops.simulation_service import SimulationService


def main() -> None:
    init_database()
    service = SimulationService()
    predictions = SimulationPredictionService(service)
    try:
        service.initialize()
        predictions.initialize()
        print(
            "Simulation metadata initialized; "
            f"removed {service.cleanup_expired()} expired artifact set(s) and "
            f"{predictions.cleanup_expired()} expired prediction result(s)."
        )
        print(f"Artifact root: {service.config.artifact_root}")
    finally:
        predictions.shutdown()
        service.shutdown()


if __name__ == "__main__":
    main()
