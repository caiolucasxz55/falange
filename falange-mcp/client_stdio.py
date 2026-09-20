"""Demo do fluxo V1 via MCP stdio: documentacao -> pre-tasks -> revisao -> banco.

O passo "a IA redige" esta fixo neste script apenas para a demo ser
reproduzivel. Na pratica quem escreve as pre-tasks e o Claude que chamou
gerar_tasks_a_partir_de_arquivo, usando o template devolvido por ela.
"""

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def conteudo(r):
    return json.loads(r.content[0].text) if r.content else None


# O que um modelo produziria lendo exemplos/documentacao_exemplo.md.
# A terceira e ruim de proposito, para o validar_task ter o que reprovar.
PRE_TASKS = [
    {
        "titulo": "Recusar ciclo de bloqueio ao definir dependencia",
        "descricao": (
            "Ao gravar bloqueada_por, percorrer a cadeia de dependencia e recusar "
            "com 409 quando o alvo levar de volta a propria task.\n"
            "Criterio de aceite: com A travando B, travar A por B retorna 409."
        ),
        "estimativa": "P",
        "bloco": "backend",
    },
    {
        "titulo": "Ignorar tasks concluidas na contagem de carga",
        "descricao": (
            "O calculo de carga conta task concluida como se fosse trabalho ativo. "
            "Filtrar por status aberto antes de somar.\n"
            "Criterio de aceite: concluir uma task reduz a carga da pessoa em 1."
        ),
        "estimativa": "PP",
        "bloco": "backend",
    },
    {
        "titulo": "Melhorias no importador",
        "descricao": "Ajustar o importador de CSV, tratar erros, etc.",
        "estimativa": "PP",
        "bloco": "backend",
    },
]


async def main():
    params = StdioServerParameters(command=sys.executable, args=["mcp_stdio_example.py"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            init = await s.initialize()
            tools = await s.list_tools()
            print(f"servidor '{init.server_info.name}' | {len(tools.tools)} tools: "
                  f"{[t.name for t in tools.tools]}\n")

            print("=" * 72)
            print("[1] gerar_tasks_a_partir_de_arquivo  (le, NAO grava nada)")
            print("=" * 72)
            r = conteudo(await s.call_tool(
                "gerar_tasks_a_partir_de_arquivo",
                {"caminho": "exemplos/documentacao_exemplo.md"},
            ))
            print(f"arquivo lido : {r['tamanho_chars']} chars")
            print(f"titulos      : {r['estrutura']['titulos'][:4]} ...")
            print(f"marcadores   : {r['estrutura']['marcadores']}")
            print(f"ja no banco  : {len(r['tasks_existentes'])} tasks")
            print(f"instrucao    : {r['instrucao'][:70]}...")

            print("\n" + "=" * 72)
            print("[2] validar_task  (revisao antes de qualquer escrita)")
            print("=" * 72)
            aprovadas = []
            for pt in PRE_TASKS:
                v = conteudo(await s.call_tool("validar_task", pt))
                marca = "OK  " if v["veredito"] == "aprovada" else "NAO "
                print(f"{marca} {pt['titulo'][:52]:<52} {v['veredito']}")
                for m in v["motivos"]:
                    print(f"       - {m}")
                if v["veredito"] == "aprovada":
                    aprovadas.append(pt)

            print("\n" + "=" * 72)
            print(f"[3] criar_task  (so as {len(aprovadas)} aprovadas viram registro)")
            print("=" * 72)
            criadas = []
            for pt in aprovadas:
                t = conteudo(await s.call_tool(
                    "criar_task", {**pt, "responsavel": "caio"}
                ))
                criadas.append(t)
                print(f"  #{t['id']} {t['titulo'][:50]:<50} [{t['estimativa']}/{t['bloco']}]")

            print("\n" + "=" * 72)
            print("[4] marcar_bloqueio  (dependencia + recusa de ciclo)")
            print("=" * 72)
            a, b = criadas[0]["id"], criadas[1]["id"]
            t = conteudo(await s.call_tool(
                "marcar_bloqueio", {"task_id": b, "bloqueada_por": a}))
            print(f"  #{b} bloqueada_por -> {t['bloqueada_por']}")
            t = conteudo(await s.call_tool(
                "marcar_bloqueio", {"task_id": a, "bloqueada_por": b}))
            print(f"  tentativa de ciclo #{a} <- #{b}: {t.get('erro')}")

            print("\n" + "=" * 72)
            print("[5] verificar_sobrecarga")
            print("=" * 72)
            print("  limite 5:", conteudo(await s.call_tool(
                "verificar_sobrecarga", {"responsavel": "caio"})))
            print("  limite 1:", conteudo(await s.call_tool(
                "verificar_sobrecarga", {"responsavel": "caio", "limite": 1})))


asyncio.run(main())
