"""Configuracao do backend, lida do .env (ou de variaveis de ambiente)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://falange:falange@127.0.0.1:5432/falange"

    # Acima de quantas tasks abertas uma pessoa/bloco e considerado sobrecarregado.
    limite_sobrecarga: int = 5


settings = Settings()
