"""Entrypoint MCP - transporte HTTP+SSE (LEGADO).

Preferir `falange_mcp/http.py` (Streamable HTTP), que e o transporte
atual do MCP. Este fica para quem tem client que so fala SSE.

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

from falange_mcp import transporte
from falange_mcp.config import settings
from falange_mcp.porteiro import Porteiro
from falange_mcp.server import build_server


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
