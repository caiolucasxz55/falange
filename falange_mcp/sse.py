"""Entrypoint MCP - transporte HTTP+SSE (para expor ao time).

    python -m falange_mcp.sse

Sobe um servidor HTTP proprio. O client aponta para uma URL:
    http://127.0.0.1:8765/sse

  GET  /sse        -> stream SSE, por onde o SERVIDOR responde
  POST /messages/  -> por onde o CLIENT envia as chamadas JSON-RPC

Esta e a porta que fica exposta ao time, e quem chega tem de trazer um
**token de conexao** (`flg_...`), gerado por uma pessoa na tela.

Antes era um segredo unico (`SSE_TOKEN`) para todo mundo, e quem passava
usava as credenciais DO SERVIDOR para falar com o backend. Isso tornava
duas pessoas conectadas a MESMA conta: `autor_id`, papel e projeto saiam
todos errados, e a identidade por pessoa da V2 morria nesta porta. Agora
cada chamada vai ao backend com a credencial de quem a fez.

O porteiro aqui confere so o FORMATO -- este processo nao tem banco. Quem
valida de verdade e o backend, que recusa com 401. Mesmo desenho do
middleware de la, e pela mesma razao.

A logica das tools esta em tools.py -- este arquivo so escolhe o transporte.
"""

import uvicorn
from starlette.responses import JSONResponse

from falange_mcp import credencial, transporte
from falange_mcp.config import settings
from falange_mcp.credencial import partes_token
from falange_mcp.server import build_server


class Porteiro:
    """Middleware ASGI cru que exige um token de conexao para deixar passar.

    ASGI puro, e nao BaseHTTPMiddleware, porque aquele embrulha a resposta e
    atrapalha o streaming do SSE. Requisicao valida passa intacta.

    So o FORMATO e conferido: este processo nao tem banco para conferir o
    hash, e nem deveria ter -- o MCP fala com o backend por HTTP e mais
    nada. Quem recusa token revogado, vencido ou inventado e o backend, na
    primeira chamada de tool.

    Barrar aqui pelo formato ainda vale: devolve 401 na conexao, em vez de
    deixar a pessoa conectar e so descobrir o problema quando a primeira
    tool falhar.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        cabecalhos = dict(scope.get("headers") or [])
        autorizacao = cabecalhos.get(b"authorization", b"").decode("latin-1")
        if partes_token(credencial.do_cabecalho(autorizacao)) is None:
            recusa = JSONResponse(
                {
                    "detail": (
                        "mande o seu token de conexao em "
                        "'Authorization: Bearer flg_...'. Gere um na tela, "
                        "em 'Conectar sua IA'"
                    )
                },
                status_code=401,
            )
            return await recusa(scope, receive, send)

        await self.app(scope, receive, send)


if __name__ == "__main__":
    # Nao ha mais aviso de "segredo vazio": a porta nao depende mais de
    # configuracao para estar fechada. Sem token de conexao no header, nao
    # entra -- e o token nao mora em arquivo nenhum do servidor, mora no
    # banco, por pessoa, revogavel na tela.
    aplicacao = build_server(
        "falange-http-sse", transporte.REMOTO
    ).sse_app(host=settings.mcp_sse_host)
    uvicorn.run(
        Porteiro(aplicacao),
        host=settings.mcp_sse_host,
        port=settings.mcp_sse_port,
    )
