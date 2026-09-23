import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'backend' / 'portal.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = BASE_DIR / "uploads"
    OUTPUT_FOLDER = BASE_DIR / "outputs"

    MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", 25))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024

    ALLOWED_EXTENSIONS = {".xlsx", ".xlsm"}
