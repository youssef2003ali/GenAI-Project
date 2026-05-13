from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str = ''
    lightrag_url: str = 'http://lightrag:9621'
    redis_url: str = 'redis://redis:6379'
    database_url: str = 'postgresql://postgres:postgres@postgres:5432/acs'
    mlflow_tracking_uri: str = 'http://mlflow:5000'

    research_model: str = 'meta-llama/llama-3.3-70b-instruct:free'
    planning_model: str = 'nousresearch/hermes-3-405b-instruct:free'
    writing_model: str = 'google/gemma-3-27b-it:free'
    editing_model: str = 'google/gemma-3-27b-it:free'
    optimization_model: str = 'google/gemma-3-12b-it:free'
    orchestrator_model: str = 'nousresearch/hermes-3-405b-instruct:free'
    gemini_api_key: str = ''

    host: str = '0.0.0.0'
    port: int = 8000
    frontend_port: int = 3000

    model_config = {'env_file': '.env', 'extra': 'ignore'}


settings = Settings()
