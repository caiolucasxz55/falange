"""Porteiro da porta HTTP do MCP, compartilhado pelos dois transportes.

Vive aqui, e nao dentro de um dos entrypoints, porque SSE e Streamable
HTTP tem de fechar a porta do MESMO jeito. Com uma copia em cada arquivo,
a tendencia e uma receber a correcao e a outra nao -- e a que ficar para
tras vira a porta aberta que ninguem lembra que existe.
"""

from starlette.responses import JSONResponse

from falange_mcp import credencial
from falange_mcp.credencial import partes_token

RECUSA = (
    "mande o seu token de conexao em 'Authorization: Bearer flg_...'. "
    "Gere um na tela, em 'Conectar sua IA'"
)


class Porteiro:
    """Middleware ASGI cru que exige um token de conexao para deixar passar.

    ASGI puro, e nao BaseHTTPMiddleware, porque aquele embrulha a resposta
    e atrapalha o streaming. Requisicao valida passa intacta.

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
            recusa = JSONResponse({"detail": RECUSA}, status_code=401)
            return await recusa(scope, receive, send)

        await self.app(scope, receive, send)
