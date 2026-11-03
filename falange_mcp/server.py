"""Monta o servidor MCP. Um lugar so registra as tools; o transporte e escolhido
pelo entrypoint (falange_mcp/stdio.py ou falange_mcp/sse.py).

Adicionar uma tool nova = colocar a funcao em tools.py e citar na lista abaixo.
Os dois transportes ganham a tool automaticamente -- inclusive o repasse de
credencial, que e feito por `_com_credencial` e nao por cada tool.
"""

import functools
import inspect
from typing import Optional

from mcp.server.mcpserver import Context, MCPServer

from falange_mcp import credencial, tools, transporte

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


def _authorization_do_contexto(ctx: Optional[Context]) -> Optional[str]:
    """O header `Authorization` da requisicao que trouxe esta chamada.

    None no stdio, onde nao ha requisicao HTTP nenhuma -- e ai a tool cai
    no `API_TOKEN` do servidor, que e o certo: o processo e do dev.
    """
    if ctx is None:
        return None
    try:
        requisicao = ctx.request_context.request
    except (AttributeError, LookupError):
        # Fora de uma chamada, ou transporte que nao carrega requisicao.
        return None
    cabecalhos = getattr(requisicao, "headers", None)
    if cabecalhos is None:
        return None
    return cabecalhos.get("authorization")


def _com_credencial(fn):
    """Embrulha a tool para ela falar com o backend como QUEM chamou.

    O wrapper ganha um parametro `ctx: Context` que a propria tool nao tem.
    O SDK detecta esse parametro pela anotacao, injeta o contexto e o
    ESCONDE do schema (`find_context_parameter` + `skip_names`), entao a
    assinatura que a IA ve continua sendo a da funcao original.

    E por isso que isto existe aqui, e nao dentro de cada tool: sao 34
    funcoes, e acrescentar um parametro em todas para resolver uma questao
    de transporte espalharia o assunto por todo o modulo.

    Duas coisas precisam ser remontadas a mao, e por motivos DIFERENTES:

    - `__signature__`, porque `functools.wraps` copia `__wrapped__` e o
      `inspect.signature` seguiria por ele ate a funcao original;
    - `__annotations__`, porque `find_context_parameter` nao olha a
      assinatura: ele chama `typing.get_type_hints(fn)`, que le as
      anotacoes -- e `wraps` acabou de copiar as da original, sem `ctx`.

    Sem a segunda, o `ctx` aparece no schema de TODAS as tools (ele deixa
    de ser reconhecido como contexto e vira parametro comum) e nunca e
    injetado. Foi o que aconteceu na primeira versao disto.
    """
    @functools.wraps(fn)
    def embrulhada(*args, ctx: Optional[Context] = None, **kwargs):
        handle = credencial.definir(
            credencial.do_cabecalho(_authorization_do_contexto(ctx))
        )
        try:
            return fn(*args, **kwargs)
        finally:
            credencial.limpar(handle)

    original = inspect.signature(fn)
    embrulhada.__signature__ = original.replace(
        parameters=[
            *original.parameters.values(),
            inspect.Parameter(
                "ctx",
                inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=Optional[Context],
            ),
        ]
    )
    embrulhada.__annotations__ = {**fn.__annotations__, "ctx": Optional[Context]}
    return embrulhada


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
        mcp.add_tool(_com_credencial(fn))
    return mcp
