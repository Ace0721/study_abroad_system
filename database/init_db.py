from pathlib import Path

from config import DB_DIR, UPLOAD_DIR
from database.db import engine
from models import Base


def initialize_database() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    initialize_database()
    print(f"Database initialized at: {Path(DB_DIR).as_posix()}")

