"""Configuracao dos servidores MCP, lida do .env (ou de variaveis de ambiente).

Nao tem DATABASE_URL de proposito: o MCP so fala com o backend por HTTP.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    backend_url: str = "http://127.0.0.1:8000"

    # Raiz permitida para gerar_tasks_a_partir_de_arquivo.
    falange_docs_root: str = "."

    # 127.0.0.1 local; no container precisa ser 0.0.0.0 para aceitar
    # conexao de fora. Definido via MCP_SSE_HOST no docker-compose.
    mcp_sse_host: str = "127.0.0.1"
    mcp_sse_port: int = 8765

    @property
    def docs_root(self) -> Path:
        return Path(self.falange_docs_root).resolve()


settings = Settings()
