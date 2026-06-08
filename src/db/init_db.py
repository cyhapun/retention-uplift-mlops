from src.db.database import init_database


def main() -> None:
    init_database()
    print("Database initialized successfully.")


if __name__ == "__main__":
    main()