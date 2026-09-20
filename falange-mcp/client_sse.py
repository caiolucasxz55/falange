"""Mesmas tools, transporte HTTP+SSE. Client aponta para URL, nao sobe processo."""

import asyncio
import json

from mcp import ClientSession
from mcp.client.sse import sse_client

URL = "http://127.0.0.1:8765/sse"


def conteudo(r):
    return json.loads(r.content[0].text) if r.content else None


async def main():
    print(f"conectando em {URL}")
    async with sse_client(URL) as (read, write):
        async with ClientSession(read, write) as s:
            init = await s.initialize()
            tools = await s.list_tools()
            print(f"servidor '{init.server_info.name}' | {len(tools.tools)} tools")
            for t in tools.tools:
                print(f"   - {t.name}")

            print("\ncontar_tasks_por_bloco ->", conteudo(await s.call_tool("contar_tasks_por_bloco", {})))
            print("verificar_sobrecarga   ->", conteudo(await s.call_tool("verificar_sobrecarga", {"bloco": "backend", "limite": 1})))
            r = conteudo(await s.call_tool("gerar_tasks_a_partir_de_arquivo", {"caminho": "exemplos/documentacao_exemplo.md"}))
            print("gerar_tasks (mesmo arq) ->", r["tamanho_chars"], "chars,", len(r["tasks_existentes"]), "tasks ja no banco")
            print("traversal bloqueado     ->", conteudo(await s.call_tool("gerar_tasks_a_partir_de_arquivo", {"caminho": "../../../../Windows/win.ini"}))["erro"][:60], "...")


asyncio.run(main())
