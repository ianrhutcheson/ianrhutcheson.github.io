from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the agent backend."""

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    symphony_api_key: str = Field('', alias='SYMPHONY_API_KEY')
    symphony_spot_agent_id: str = Field(
        '3d8364d0-cfd0-4d16-95c9-1505fa747e10', alias='SYMPHONY_SPOT_AGENT_ID'
    )
    symphony_base_url: str = Field('https://api.symphony.finance', alias='SYMPHONY_BASE_URL')

    openai_api_key: str = Field('', alias='OPENAI_API_KEY')
    serpapi_api_key: str = Field('', alias='SERPAPI_API_KEY')

    database_url: str = Field('postgresql+psycopg://postgres:postgres@localhost:5432/monad_agent', alias='DATABASE_URL')


settings = Settings()
