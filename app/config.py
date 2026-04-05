from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DEBUG: bool = False
    LOG_DIR: str = "/app/storage/logs"
    LLM_MODEL: str = "qwen3-8b-12k:latest"
    LLM_TEMPERATURE: float = 0.0
    EMBEDDING_MODEL: str = "bge-m3:latest"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.55
    RETRIEVAL_FALLBACK_THRESHOLD: float = 0.35
    RAPTOR_ENABLED: bool = True
    RAPTOR_MAX_UNITS_PER_DOCUMENT: int = 2
    RAPTOR_MAX_UNIT_CHARS: int = 1500

    # Server Configuration
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DATABASE_URL: str = (
        "postgres://postgres:postgres@localhost:5432/postgres?sslmode=disable"
    )
    STORAGE_PATH: str = "/app/storage"
    CONVERSATION_HISTORY_LIMIT: int = 8

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
