from app.config import Settings


def test_settings_load():
    """
    Test that the default settings are correctly loaded.
    """
    settings = Settings()
    assert settings.LLM_MODEL is not None
    assert settings.LLM_TEMPERATURE == 0.0
    assert settings.OLLAMA_BASE_URL.startswith("http")
    assert len(settings.OLLAMA_BASE_URL) > 10


def test_settings_overridable():
    """
    Test that settings can be overridden.
    """
    settings = Settings(LLM_MODEL="test-model", PORT=9000)
    assert settings.LLM_MODEL == "test-model"
    assert settings.PORT == 9000
