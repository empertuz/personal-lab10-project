from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_PATH: str = "./data/pluvioapp.db"
    DATA_DIR: str = "./resources/data"
    CATALOG_PATH: str = "./resources/data/CNE_IDEAM.csv"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    LOG_LEVEL: str = "info"
    ADMIN_KEY: str = "changeme"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def database_path_resolved(self) -> Path:
        return Path(self.DATABASE_PATH).resolve()

    @property
    def data_dir_resolved(self) -> Path:
        return Path(self.DATA_DIR).resolve()

    @property
    def catalog_path_resolved(self) -> Path:
        return Path(self.CATALOG_PATH).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
