import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass
class Settings:
    max_upload_bytes: int
    db_backend: str
    sqlite_path: str
    vertex_ai_project_id: str
    vertex_ai_location: str
    jwt_secret_key: str
    jwt_algorithm: str


def _get_float(name: str, default: float) -> float:
    try:
        val = os.getenv(name)
        return float(val) if val is not None else default
    except Exception:
        return default


def _get_int(name: str, default: int) -> int:
    try:
        val = os.getenv(name)
        return int(val) if val is not None else default
    except Exception:
        return default

def get_settings() -> Settings:
    # Default upload limit ~6MB
    max_upload_bytes = _get_int("MAX_UPLOAD_BYTES", 6 * 1024 * 1024)

    # Database config (defaults for dev)
    db_backend = os.getenv("DB_BACKEND", "sqlite").lower()
    sqlite_path = os.getenv("SQLITE_PATH", os.path.join(os.getcwd(), "data", "app.db"))

    # Vertex AI / Gemini config
    vertex_ai_project_id = os.getenv("VERTEX_AI_PROJECT_ID", "your-gcp-project-id") # Default for local dev if not set
    vertex_ai_location = os.getenv("VERTEX_AI_LOCATION", "us-east1") # Default for local dev if not set
    
    # Auth config
    jwt_secret_key = os.getenv("JWT_SECRET_KEY", "changeme_dev_secret")
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    return Settings(
        max_upload_bytes=max_upload_bytes,
        db_backend=db_backend,
        sqlite_path=sqlite_path,
        vertex_ai_project_id=vertex_ai_project_id,
        vertex_ai_location=vertex_ai_location,
        jwt_secret_key=jwt_secret_key,
        jwt_algorithm=jwt_algorithm,
    )
