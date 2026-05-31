from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    identity_ttl: int = 600
    hsv_match_threshold: float = 0.7
    height_match_threshold: float = 0.15

    camera_sources: str = "rtsp://localhost:8554/cam0,rtsp://localhost:8555/cam1"
    detection_confidence: float = 0.5
    detection_interval: int = 1

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    sqlite_db_path: str = "data/persons.db"

    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    video_file: str = "example/CCTV_example.mp4"
    rtsp_port_start: int = 8554

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def camera_list(self) -> List[str]:
        return [c.strip() for c in self.camera_sources.split(",") if c.strip()]

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
