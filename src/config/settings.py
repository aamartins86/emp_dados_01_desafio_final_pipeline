"""Carregamento centralizado das configurações do projeto."""

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_schema: str
    silver_schema: str
    gold_schema: str
    db_user: str
    db_password: str
    bronze_path: Path
    log_dir: Path
    log_level: str
    http_timeout_seconds: float

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        load_dotenv(env_file or PROJECT_ROOT / ".env")
        db_user = os.getenv("DB_USER", "").strip()
        if not db_user:
            raise ValueError("DB_USER não foi preenchido no arquivo .env")

        return cls(
            db_host=os.getenv("DB_HOST", "localhost"),
            db_port=int(os.getenv("DB_PORT", "5432")),
            db_name=os.getenv("DB_NAME", "db_emp_dados_junior"),
            db_schema=os.getenv("DB_SCHEMA", "bronze"),
            silver_schema=os.getenv("DB_SCHEMA_PRATA", "prata"),
            gold_schema=os.getenv("DB_SCHEMA_OURO", "ouro"),
            db_user=db_user,
            db_password=os.getenv("DB_PASSWORD", ""),
            bronze_path=PROJECT_ROOT / os.getenv("DATA_BRONZE_PATH", "data/bronze"),
            log_dir=PROJECT_ROOT / os.getenv("LOG_DIR", "logs"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            http_timeout_seconds=float(os.getenv("HTTP_TIMEOUT_SECONDS", "30")),
        )
