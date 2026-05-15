from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str = ''
    mistral_api_key: str = ''
    mistral_model: str = 'mistral-large-latest'
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-2.0-flash'
    lightrag_url: str = 'http://lightrag:9621'
    redis_url: str = 'redis://redis:6379'
    database_url: str = 'postgresql://postgres:postgres@postgres:5432/acs'
    mlflow_tracking_uri: str = 'http://mlflow:5000'

    research_model: str = 'mistral-large-latest'
    planning_model: str = 'mistral-large-latest'
    writing_model: str = 'mistral-large-latest'
    editing_model: str = 'mistral-large-latest'
    optimization_model: str = 'mistral-small-latest'
    orchestrator_model: str = 'mistral-large-latest'
    host: str = '0.0.0.0'
    port: int = 8000
    frontend_port: int = 3000

    model_config = {'env_file': '.env', 'extra': 'ignore'}


settings = Settings()
