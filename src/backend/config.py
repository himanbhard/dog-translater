import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass
class Settings:
    max_upload_bytes: int
    db_backend: str
    sqlite_path: str
    bedrock_region: str
    bedrock_model_id: str
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
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

    # Bedrock config
    bedrock_region = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "meta.llama3-2-11b-instruct-v1:0")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    # Auth config
    jwt_secret_key = os.getenv("JWT_SECRET_KEY", "changeme_dev_secret")
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    return Settings(
        max_upload_bytes=max_upload_bytes,
        db_backend=db_backend,
        sqlite_path=sqlite_path,
        bedrock_region=bedrock_region,
        bedrock_model_id=bedrock_model_id,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        jwt_secret_key=jwt_secret_key,
        jwt_algorithm=jwt_algorithm,
    )
