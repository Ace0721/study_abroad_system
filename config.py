from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
UPLOAD_DIR = ASSETS_DIR / "uploads"
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "study_abroad.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# SQLite config.
SQLITE_CONNECT_ARGS = {"check_same_thread": False}

# Local Ollama + DeepSeek settings for AI assistant.
OLLAMA_OPENAI_BASE_URL = "http://localhost:11434/v1/"
OLLAMA_OPENAI_API_KEY = "ollama"
OLLAMA_DEEPSEEK_MODEL = "deepseek-r1:8b"
OLLAMA_TIMEOUT_SECONDS = 30
