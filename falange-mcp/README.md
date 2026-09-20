# Falange V1 - backend + MCP

Backend FastAPI sobre Postgres, exposto a uma IA por dois transportes MCP.

## Arquitetura

    IA (client MCP)
       |  stdio (local)          SSE (time)
       v                          v
    mcp_stdio_example.py    mcp_http_sse_example.py
       \                        /
        falange_mcp/server.py  <- registra as tools uma vez so
        falange_mcp/tools.py   <- logica, nao sabe o que e transporte
                |
                | HTTP
                v
        backend/ (FastAPI) -> Postgres

Regra: o MCP nunca fala com o Postgres direto. Sempre via HTTP. Uma fonte
de verdade so, e os dois transportes ficam sendo cascas finas.

## Setup

1. Criar banco e role (como superusuario do Postgres):

   ```sql
   CREATE ROLE falange LOGIN PASSWORD 'troque-isto';
   CREATE DATABASE falange OWNER falange;
   ```

2. `cp .env.example .env` e preencher a `DATABASE_URL` com essa senha.

3. Instalar e migrar:

   ```
   .venv/Scripts/python -m pip install -r requirements.txt
   .venv/Scripts/alembic upgrade head
   ```

4. Subir:

   ```
   .venv/Scripts/python -m uvicorn backend.main:app --port 8000   # backend
   .venv/Scripts/python mcp_stdio_example.py                      # MCP local
   .venv/Scripts/python mcp_http_sse_example.py                   # MCP :8765
   ```

5. Demo do fluxo documentacao -> tasks:

   ```
   .venv/Scripts/python client_stdio.py
   ```

## Tools

| Tool | Escreve no banco? |
|---|---|
| `criar_task` | sim |
| `listar_tasks` | nao |
| `marcar_bloqueio` | sim (recusa ciclo e auto-bloqueio) |
| `contar_tasks_por_bloco` | nao |
| `verificar_sobrecarga` | nao |
| `gerar_tasks_a_partir_de_arquivo` | **nao** - so sugere, para voce revisar |
| `validar_task` | nao |

`gerar_tasks_a_partir_de_arquivo` le o arquivo e devolve conteudo,
estrutura extraida, o template e as tasks existentes. Quem redige as
pre-tasks e a IA que chamou. `validar_task` aplica lint deterministico
(tamanho, enchimento, criterio de aceite, coerencia da estimativa,
duplicata) - nao depende do humor do modelo.

## Adicionar uma tool

1. Escrever a funcao em `falange_mcp/tools.py`.
2. Citar na tupla `TOOLS` em `falange_mcp/server.py`.

Os dois transportes ganham a tool automaticamente.

## Fora do escopo do V1

Frontend, gamificacao/war room, autenticacao e multi-usuario. `responsavel`
e texto simples de proposito - vira FK para usuario no V2.
