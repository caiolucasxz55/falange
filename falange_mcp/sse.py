"""Entrypoint MCP - transporte HTTP+SSE (para expor ao time).

    python -m falange_mcp.sse

Sobe um servidor HTTP proprio. O client aponta para uma URL:
    http://127.0.0.1:8765/sse

  GET  /sse        -> stream SSE, por onde o SERVIDOR responde
  POST /messages/  -> por onde o CLIENT envia as chamadas JSON-RPC

A logica das tools esta em tools.py -- este arquivo so escolhe o transporte.
"""

from falange_mcp.config import settings
from falange_mcp.server import build_server

if __name__ == "__main__":
    build_server("falange-http-sse").run(
        transport="sse", host=settings.mcp_sse_host, port=settings.mcp_sse_port
    )
