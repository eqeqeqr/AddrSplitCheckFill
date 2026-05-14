from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULT_DIR = DATA_DIR / "results"
DB_PATH = DATA_DIR / "address.db"
DEFAULT_SAMPLE_SIZE = 100
REDIS_URL = "redis://127.0.0.1:6379/0"

for directory in (DATA_DIR, UPLOAD_DIR, RESULT_DIR):
    directory.mkdir(parents=True, exist_ok=True)
