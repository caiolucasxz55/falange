"""Entrypoint MCP - transporte STDIO (uso local, na sua maquina).

    python -m falange_mcp.stdio

O client executa isto como subprocesso e fala JSON-RPC por stdin/stdout.
Sem porta, sem URL. NUNCA use print() aqui: stdout e o canal do protocolo.

A logica das tools esta em tools.py -- este arquivo so escolhe o transporte.
"""

from falange_mcp import transporte
from falange_mcp.server import build_server

if __name__ == "__main__":
    servidor = build_server("falange-stdio", transporte.LOCAL)
    servidor.run(transport="stdio")
