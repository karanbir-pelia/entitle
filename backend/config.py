from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    model_backend: Literal["ollama", "gemini_api"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"
    gemini_api_key: str = ""
    gemini_model: str = "gemma-4-26b-a4b-it"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    max_tokens: int = 2048
    model_timeout_seconds: float = 600.0
    enable_thinking: bool = True
    default_language: str = "en"

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "protected_namespaces": ("settings_",),
    }


settings = Settings()
