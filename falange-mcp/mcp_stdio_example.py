"""Entrypoint MCP - transporte STDIO (uso local, na sua maquina).

O client executa este arquivo como subprocesso e fala JSON-RPC por
stdin/stdout. Sem porta, sem URL. NUNCA use print() aqui: stdout e o
canal do protocolo.

A logica das tools esta em falange_mcp/tools.py -- este arquivo so escolhe
o transporte.
"""

from falange_mcp.server import build_server

if __name__ == "__main__":
    build_server("falange-stdio").run(transport="stdio")
