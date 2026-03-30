from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LLM_MODEL: str = "qwen3:8b-16k"
    LLM_TEMPERATURE: float = 0.0
    EMBEDDING_MODEL: str = "bge-m3:latest"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.55

    # Server Configuration
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DATABASE_URL: str = (
        "postgres://postgres:postgres@localhost:5432/postgres?sslmode=disable"
    )
    STORAGE_PATH: str = "/app/storage"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
