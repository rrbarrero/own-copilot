from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LLM_MODEL: str = "qwen3:8b-16k"
    LLM_TEMPERATURE: float = 0.0
    OLLAMA_BASE_URL: str = "http://192.168.1.164:11434"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

