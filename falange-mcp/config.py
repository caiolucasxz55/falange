"""Configuracao unica, lida do .env. Usada pelo backend e pelos servidores MCP."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://falange:falange@127.0.0.1:5432/falange"
    falange_docs_root: str = "."
    limite_sobrecarga: int = 5
    backend_url: str = "http://127.0.0.1:8000"

    # 127.0.0.1 local; no container precisa ser 0.0.0.0 para aceitar
    # conexao de fora. Definido via MCP_SSE_HOST no docker-compose.
    mcp_sse_host: str = "127.0.0.1"
    mcp_sse_port: int = 8765

    @property
    def docs_root(self) -> Path:
        return Path(self.falange_docs_root).resolve()


settings = Settings()
