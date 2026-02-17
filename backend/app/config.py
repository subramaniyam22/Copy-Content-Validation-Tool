import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # === Azure OpenAI ===
    OPENAI_API_KEY: str = ""
    AZURE_ENDPOINT: str = ""
    API_VERSION: str = "2024-02-01"
    MODEL_NAME: str = "g5-website-validation-gpt-4.1-nano"
    EMBEDDING_MODEL: str = "text-embedding-ada-002"

    # === Database ===
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/content_validator"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/content_validator"

    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"

    # === CORS ===
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # === Storage ===
    STORAGE_BACKEND: str = "local"  # local | s3
    LOCAL_STORAGE_DIR: str = "./storage"
    S3_BUCKET: str = ""
    S3_REGION: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # === Crawl Limits ===
    MAX_CRAWL_PAGES: int = 50
    MAX_CRAWL_DEPTH: int = 3
    MAX_CRAWL_BYTES: int = 50_000_000  # 50MB total
    SCRAPE_TIMEOUT_MS: int = 30000
    CRAWL_TIMEOUT_MS: int = 60000

    # === Upload Limits ===
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_UPLOAD_EXTENSIONS: str = ".pdf,.docx,.txt,.xlsx,.csv"

    # === Paths ===
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [e.strip() for e in self.ALLOWED_UPLOAD_EXTENSIONS.split(",") if e.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.LOCAL_STORAGE_DIR, "guidelines"), exist_ok=True)
os.makedirs(os.path.join(settings.LOCAL_STORAGE_DIR, "exports"), exist_ok=True)
