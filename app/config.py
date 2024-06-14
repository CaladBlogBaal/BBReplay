from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL")
    api_key: str = os.getenv("API_KEY")
    secret: str = os.getenv("SECRET_KEY")

    class Config:
        env_file = ".env"


settings = Settings()
