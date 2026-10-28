from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Deployed workers have no .env file and read the same names from the environment.
    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".env", extra="ignore")

    deepgram_api_key: SecretStr
    cerebras_api_key: SecretStr
    groq_api_key: SecretStr
    cartesia_api_key: SecretStr
    database_url: SecretStr
    # DEMO_KEY works without signup but allows only 30 requests per hour.
    fdc_api_key: SecretStr = SecretStr("DEMO_KEY")


# Pyright can't see that pydantic-settings fills the fields from the environment.
settings = Settings()  # pyright: ignore[reportCallIssue]
