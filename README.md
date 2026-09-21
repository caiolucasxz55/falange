# Falange V1 - backend + MCP

Backend FastAPI sobre Postgres, exposto a uma IA por dois transportes MCP.

## Arquitetura

    IA (client MCP)
       |  stdio (local)          SSE (time)
       v                          v
    falange_mcp/stdio.py     falange_mcp/sse.py
       \                        /
        falange_mcp/server.py  <- registra as tools uma vez so
        falange_mcp/tools.py   <- logica, nao sabe o que e transporte
                |
                | HTTP
                v
        backend/ (FastAPI) -> Postgres

Regra: o MCP nunca fala com o Postgres direto. Sempre via HTTP. Uma fonte
de verdade so, e os dois transportes ficam sendo cascas finas.

## Subir tudo (Docker)

    cp .env.example .env        # ajuste POSTGRES_PASSWORD
    docker compose up -d --build

| Servico | Host | Papel |
|---|---|---|
| `db` | `localhost:5433` | Postgres 18, volume `pgdata` |
| `migrate` | - | roda `alembic upgrade head` e sai |
| `backend` | `localhost:8010` | API FastAPI |
| `mcp-sse` | `localhost:8765` | servidor MCP para o time |

Portas do host escolhidas para nao colidir com o que ja roda nesta maquina:
5432 e do Postgres nativo, 8000 e 8001 sao de outros projetos.

O `stdio` nao vira servico: por definicao e um subprocesso que o client
local sobe, nao um servidor que fica escutando.

O `backend` tem healthcheck e o `mcp-sse` so sobe depois dele responder.
O `migrate` roda como servico separado, entao a migration nao duplica
quando houver mais de uma replica do backend.

Checar:

    curl http://localhost:8010/health
    docker compose logs migrate

Dados sobrevivem a `docker compose down`. Para zerar: `docker compose down -v`.

## Rodar sem Docker

Precisa de um Postgres proprio e da `DATABASE_URL` no `.env`:

    python -m venv .venv
    .venv/Scripts/python -m pip install -r requirements.txt
    .venv/Scripts/alembic upgrade head
    .venv/Scripts/python -m uvicorn backend.main:app --port 8000
    .venv/Scripts/python -m falange_mcp.sse

## Frontend de teste

Tela minima em Next.js para ver o fluxo MCP -> backend. Detalhes em
`frontend/README.md`.

    cd frontend && npm install && npm run dev     # http://localhost:3010

O backend libera CORS so para as origens em `CORS_ORIGINS` (padrao
`http://localhost:3010`).

## Configuracao

Cada pacote tem a sua, lida do `.env` ou de variaveis de ambiente:

| Arquivo | Le |
|---|---|
| `backend/config.py` | `DATABASE_URL`, `LIMITE_SOBRECARGA`, `CORS_ORIGINS` |
| `falange_mcp/config.py` | `BACKEND_URL`, `FALANGE_DOCS_ROOT`, `MCP_SSE_HOST`, `MCP_SSE_PORT` |

O MCP nao conhece `DATABASE_URL` de proposito: nao tem como falar com o
banco nem por engano.

## Tools

| Tool | Escreve no banco? |
|---|---|
| `criar_task` | sim |
| `listar_tasks` | nao |
| `editar_task` | sim (alteracao parcial) |
| `apagar_task` | sim |
| `marcar_bloqueio` | sim (recusa ciclo e auto-bloqueio) |
| `mudar_status` | sim (concluir limpa o bloqueio) |
| `contar_tasks_por_bloco` | nao |
| `verificar_sobrecarga` | nao |
| `gerar_tasks_a_partir_de_arquivo` | **nao** - so sugere, para voce revisar |
| `validar_task` | nao |

Nenhuma tool levanta excecao para erro previsivel: devolve
`{"erro": "<frase>"}`. Quem le isso e um modelo, e uma excecao vira
`Error executing tool X` do lado do client, que nao diz o que corrigir.

`gerar_tasks_a_partir_de_arquivo` le o arquivo e devolve conteudo,
estrutura extraida, o template e as tasks existentes. Quem redige as
pre-tasks e a IA que chamou. `validar_task` aplica lint deterministico
(tamanho, enchimento, criterio de aceite, coerencia da estimativa,
duplicata) - nao depende do humor do modelo.

A leitura de arquivo e limitada a `FALANGE_DOCS_ROOT` (`/app/exemplos` no
container). Caminho absoluto ou `../` fora dessa raiz e recusado - importa
porque o `mcp-sse` e o que fica exposto ao time.

## Conectar o Claude

**Claude Code** - o `.mcp.json` na raiz do projeto ja esta pronto. Suba a
stack e abra o projeto; o servidor `falange` aparece com as 10 tools.

**Claude Desktop** - em `%APPDATA%\Claude\claude_desktop_config.json`:

    {
      "mcpServers": {
        "falange": {
          "command": "C:/caminho/para/falange/.venv/Scripts/python.exe",
          "args": ["-m", "falange_mcp.stdio"],
          "env": {
            "PYTHONPATH": "C:/caminho/para/falange",
            "BACKEND_URL": "http://127.0.0.1:8010",
            "FALANGE_DOCS_ROOT": "C:/caminho/para/falange"
          }
        }
      }
    }

Caminho absoluto e `env` explicito sao obrigatorios: o stdio nao herda o
environment de quem chamou. O `PYTHONPATH` e o que permite o `-m` achar o
pacote independente do diretorio de onde o client dispara o processo. O `.mcp.json` versionado tem caminhos desta
maquina - quem clonar precisa ajustar.

## Adicionar uma tool

1. Escrever a funcao em `falange_mcp/tools.py`.
2. Citar na tupla `TOOLS` em `falange_mcp/server.py`.

Os dois transportes ganham a tool automaticamente.

## Pegadinhas ja resolvidas

- `postgres:18+` exige o volume em `/var/lib/postgresql`, nao em
  `/var/lib/postgresql/data`; com o caminho antigo a imagem aborta.
- `stdio_client` NAO herda o environment do processo pai: passe
  `env=dict(os.environ)` em `StdioServerParameters`, senao o subprocesso
  perde `BACKEND_URL` e afins.
- O servidor SSE precisa de `MCP_SSE_HOST=0.0.0.0` dentro de container;
  em `127.0.0.1` ele nao aceita conexao de fora.
- `docker compose run` usa a imagem construida, nao os arquivos locais:
  editou codigo, rebuilde antes de testar.
- A imagem e `slim`: nao tem `curl` nem `wget`. O healthcheck usa `python
  -c urllib.request`.

## Fora do escopo do V1

Frontend de verdade (o atual e so tela de teste), gamificacao/war room, autenticacao e multi-usuario. `responsavel`
e texto simples de proposito - vira FK para usuario no V2.
