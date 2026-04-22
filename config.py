from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
UPLOAD_DIR = ASSETS_DIR / "uploads"
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "study_abroad.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# SQLite 配置：课程作业单机模式，保留 WAL 以提升稳定性。
SQLITE_CONNECT_ARGS = {"check_same_thread": False}
