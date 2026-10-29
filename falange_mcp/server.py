"""Monta o servidor MCP. Um lugar so registra as tools; o transporte e escolhido
pelo entrypoint (falange_mcp/stdio.py ou falange_mcp/sse.py).

Adicionar uma tool nova = colocar a funcao em tools.py e citar na lista abaixo.
Os dois transportes ganham a tool automaticamente.
"""

from mcp.server.mcpserver import MCPServer

from falange_mcp import tools, transporte

TOOLS = (
    tools.criar_task,
    tools.listar_tasks,
    tools.editar_task,
    tools.apagar_task,
    tools.adicionar_dependencia,
    tools.remover_dependencia,
    tools.mudar_status,
    tools.contar_tasks_por_bloco,
    tools.verificar_sobrecarga,
    tools.gerar_tasks_a_partir_de_arquivo,
    tools.validar_task,
    tools.sugerir_proximas,
    tools.ver_calibracao,
    tools.ver_autonomia,
    tools.definir_autonomia,
    tools.registrar_decisao,
    tools.ver_perfil,
    tools.registrar_preferencia,
    tools.listar_preferencias,
    tools.confirmar_preferencia,
    tools.desativar_preferencia,
    tools.ver_projeto,
    tools.ver_configuracao,
    tools.definir_configuracao,
    tools.registrar_nota,
    tools.listar_notas,
    tools.resolver_nota,
    tools.editar_nota,
    tools.apagar_nota,
    tools.coletar_evidencias,
    tools.ver_diff_do_commit,
    tools.registrar_evidencia,
    tools.listar_evidencias,
    tools.apagar_evidencia,
)


def build_server(name: str, transporte_servido: str) -> MCPServer:
    """Monta o servidor e DECLARA que transporte ele serve.

    O transporte e parametro obrigatorio, nao deducao a partir de `name`:
    `coletar_evidencias` roda git no disco local e precisa recusar quando o
    processo esta longe do repositorio de quem chamou. Errar isso em
    silencio faria a tool ler um repositorio que nao e de ninguem.
    """
    transporte.definir(transporte_servido)
    mcp = MCPServer(name=name)
    for fn in TOOLS:
        mcp.add_tool(fn)
    return mcp
