from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Uygulama ──
    allowed_origins: str = "http://localhost:3000"
    upload_dir: str = "uploads"
    max_file_size_mb: int = 500

    # ── PostgreSQL ──
    postgres_user: str = "veradeep"
    postgres_password: str = "veradeep_secret"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "veradeep_db"

    # İsteğe bağlı: Tam bağlantı stringi (.env'de override edilebilir)
    database_url: str | None = None

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def db_url(self) -> str:
        """SQLAlchemy + asyncpg bağlantı stringini döndürür."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def db_url_sync(self) -> str:
        """Senkron (psycopg2) bağlantı stringini döndürür (migration vb. için)."""
        if self.database_url:
            return self.database_url.replace("+asyncpg", "")
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
