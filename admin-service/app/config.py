import os


def optional_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


class Settings:
    service_name: str = os.environ["SERVICE_NAME"]
    auth_database_url: str = os.environ["AUTH_DATABASE_URL"]
    user_database_url: str = os.environ["USER_DATABASE_URL"]
    lobby_database_url: str = os.environ["LOBBY_DATABASE_URL"]
    redis_host: str = optional_env("REDIS_HOST", "redis")
    redis_port: int = int(optional_env("REDIS_PORT", "6379"))
    redis_db: int = int(optional_env("REDIS_DB", "0"))
    redis_key_prefix: str = optional_env("REDIS_KEY_PREFIX", "bingo")
    jwt_secret_key: str = os.environ["JWT_SECRET_KEY"]
    jwt_algorithm: str = os.environ["JWT_ALGORITHM"]
    cors_origins: str = os.environ["CORS_ORIGINS"]
    admin_username: str = optional_env("ADMIN_USERNAME", "admin")
    admin_password: str = optional_env("ADMIN_PASSWORD", "admin")
    internal_service_token: str = optional_env("INTERNAL_SERVICE_TOKEN")
    auth_service_url: str = optional_env("AUTH_SERVICE_URL")
    user_service_url: str = optional_env("USER_SERVICE_URL")
    lobby_service_url: str = optional_env("LOBBY_SERVICE_URL")

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
