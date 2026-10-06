"""Configuracao dos servidores MCP, lida do .env (ou de variaveis de ambiente).

Nao tem DATABASE_URL de proposito: o MCP so fala com o backend por HTTP.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Caminho absoluto de proposito: o stdio_client NAO herda o ambiente de quem
# o chamou, e o subprocesso pode nascer em qualquer diretorio. Com caminho
# relativo o .env simplesmente nao seria encontrado, e o token ficaria vazio
# sem ninguem perceber.
_RAIZ = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_RAIZ / ".env", extra="ignore")

    backend_url: str = "http://127.0.0.1:8000"

    # Raiz permitida para gerar_tasks_a_partir_de_arquivo.
    falange_docs_root: str = "."

    # 127.0.0.1 local; no container precisa ser 0.0.0.0 para aceitar
    # conexao de fora. Definido via MCP_SSE_HOST no docker-compose.
    mcp_sse_host: str = "127.0.0.1"
    mcp_sse_port: int = 8765

    # Token que o MCP apresenta ao backend. Mora no .env (fora do git), nunca
    # no .mcp.json, que e versionado.
    api_token: str = ""

    # Token que o PROPRIO servidor SSE exige de quem se conecta nele. E uma
    # porta diferente da do backend: quem alcanca o SSE usa as credenciais do
    # servidor, entao protege-la com o mesmo segredo nao separaria nada.
    sse_token: str = ""

    @property
    def docs_root(self) -> Path:
        return Path(self.falange_docs_root).resolve()


settings = Settings()
