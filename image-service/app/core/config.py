from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    hf_model: str = "segmind/tiny-sd"
    image_size: int = 512
    num_inference_steps: int = 8
    images_dir: str = "/data/images"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
