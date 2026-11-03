"""Entrypoint MCP - transporte Streamable HTTP (para expor ao time).

    python -m falange_mcp.http

Sobe um servidor HTTP proprio. O client aponta para uma URL:
    http://127.0.0.1:8765/mcp

Substitui o SSE (`falange_mcp/sse.py`), que continua no repositorio para
quem tem client antigo. Streamable HTTP e o transporte atual do MCP: um
endpoint so, que responde JSON direto quando a resposta e curta e abre
stream quando precisa, em vez do par GET /sse + POST /messages/.

Esta e a porta que fica exposta ao time, e quem chega tem de trazer um
**token de conexao** (`flg_...`), gerado por uma pessoa na tela. O porteiro
confere so o FORMATO -- este processo nao tem banco. Quem valida de
verdade e o backend, que recusa com 401. Mesmo desenho do middleware de la,
e pela mesma razao.

A logica das tools esta em tools.py -- este arquivo so escolhe o transporte.
"""

import uvicorn

from falange_mcp import transporte
from falange_mcp.config import settings
from falange_mcp.porteiro import Porteiro
from falange_mcp.server import build_server

CAMINHO = "/mcp"

if __name__ == "__main__":
    aplicacao = build_server(
        "falange-http", transporte.REMOTO
    ).streamable_http_app(
        streamable_http_path=CAMINHO,
        host=settings.mcp_sse_host,
    )
    uvicorn.run(
        Porteiro(aplicacao),
        host=settings.mcp_sse_host,
        port=settings.mcp_sse_port,
    )
