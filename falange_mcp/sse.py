"""Entrypoint MCP - transporte HTTP+SSE (para expor ao time).

    python -m falange_mcp.sse

Sobe um servidor HTTP proprio. O client aponta para uma URL:
    http://127.0.0.1:8765/sse

  GET  /sse        -> stream SSE, por onde o SERVIDOR responde
  POST /messages/  -> por onde o CLIENT envia as chamadas JSON-RPC

Esta e a porta que fica exposta ao time, entao ela tem porteiro proprio
(FALANGE_SSE_TOKEN). Quem passa por aqui usa as credenciais do servidor para
falar com o backend: sem o porteiro, alcancar a porta ja seria ter acesso
total as tools.

A logica das tools esta em tools.py -- este arquivo so escolhe o transporte.
"""

import uvicorn
from starlette.responses import JSONResponse

from falange_mcp.config import settings
from falange_mcp.seguranca import token_valido
from falange_mcp.server import build_server


class Porteiro:
    """Middleware ASGI cru que exige o token antes de deixar passar.

    ASGI puro, e nao BaseHTTPMiddleware, porque aquele embrulha a resposta e
    atrapalha o streaming do SSE. Requisicao valida passa intacta.
    """

    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.token:
            return await self.app(scope, receive, send)

        cabecalhos = dict(scope.get("headers") or [])
        autorizacao = cabecalhos.get(b"authorization", b"").decode("latin-1")
        if not token_valido(autorizacao, self.token):
            recusa = JSONResponse(
                {"detail": "token invalido ou ausente"}, status_code=401
            )
            return await recusa(scope, receive, send)

        await self.app(scope, receive, send)


if __name__ == "__main__":
    if not settings.sse_token:
        # Barulhento de proposito: esta e a porta que o time alcanca.
        print("ATENCAO: SSE_TOKEN vazio, qualquer um na rede usa as tools")

    aplicacao = build_server("falange-http-sse").sse_app(host=settings.mcp_sse_host)
    uvicorn.run(
        Porteiro(aplicacao, settings.sse_token),
        host=settings.mcp_sse_host,
        port=settings.mcp_sse_port,
    )
