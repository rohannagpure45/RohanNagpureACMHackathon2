import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DATA_DIR = BASE_DIR / "data"
VIDEO_DIR = DATA_DIR / "videos"
UPLOAD_DIR = DATA_DIR / "uploads"
MODEL_DIR = BASE_DIR / "backend" / "models"
DB_PATH = DATA_DIR / "fatigue_detection.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
