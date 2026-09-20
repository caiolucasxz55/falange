"""Monta o servidor MCP. Um lugar so registra as tools; o transporte e escolhido
pelo entrypoint (mcp_stdio_example.py ou mcp_http_sse_example.py).

Adicionar uma tool nova = colocar a funcao em tools.py e citar na lista abaixo.
Os dois transportes ganham a tool automaticamente.
"""

from mcp.server.mcpserver import MCPServer

from falange_mcp import tools

TOOLS = (
    tools.criar_task,
    tools.listar_tasks,
    tools.editar_task,
    tools.apagar_task,
    tools.marcar_bloqueio,
    tools.mudar_status,
    tools.contar_tasks_por_bloco,
    tools.verificar_sobrecarga,
    tools.gerar_tasks_a_partir_de_arquivo,
    tools.validar_task,
)


def build_server(name: str) -> MCPServer:
    mcp = MCPServer(name=name)
    for fn in TOOLS:
        mcp.add_tool(fn)
    return mcp
