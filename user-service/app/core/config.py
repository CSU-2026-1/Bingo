from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    rabbitmq_url: str
    user_events_exchange: str
    user_registered_routing_key: str
    user_registered_queue: str
    cors_origins: str
    auth_service_url: str
    internal_service_token: str
    http_timeout_seconds: float = 5
    ollama_url: str = ""
    ollama_model: str = ""
    image_service_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
