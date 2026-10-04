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
          |
          +-- priorizacao.py   <- modulo puro: recebe dados, devolve dados
          +-- calibracao.py    <- modulo puro: estimado x duracao real
          +-- perfil.py        <- modulo puro: decisoes viram padroes
          +-- autonomia.py     <- modulo puro: promocao e rebaixamento

Regra do calculo: o que e juizo (ranking, limiares, alertas) mora em modulo
puro no backend, sem sessao e sem HTTP. A IA redige e conversa; o codigo
calcula e julga. A tela consome o mesmo resultado por endpoint.

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
| `gerar_tasks_a_partir_de_arquivo` | **nao** - aceita arquivo ou pasta; so sugere, para voce revisar |
| `validar_task` | nao |
| `sugerir_proximas` | nao (ranking explicado) |
| `ver_calibracao` | nao (estimado x real) |
| `ver_perfil` | nao (o que o time ensinou) |
| `ver_autonomia` | nao (niveis e promocao) |
| `definir_autonomia` | sim (muda o nivel) |
| `registrar_decisao` | sim (memoria da escolha) |
| `registrar_preferencia` | sim (inferida nasce inativa) |
| `listar_preferencias` | nao |
| `confirmar_preferencia` | sim (ativa) |
| `desativar_preferencia` | sim (desliga) |
| `ver_configuracao` | nao |
| `definir_configuracao` | sim (liga/desliga as perguntas) |
| `registrar_nota` | sim (nota, nao task) |
| `listar_notas` | nao |
| `resolver_nota` | sim (marca resolvida) |
| `editar_nota` | sim (tambem reabre) |
| `apagar_nota` | sim (remove de vez) |

Notas sao o registro solto do time (problema, decisao ou duvida) para nao
abrir task bloqueada so para discutir. Sobrevivem a exclusao da task ligada,
com `task_id` voltando a null. `resolver_nota` encerra sem apagar,
`editar_nota` com `resolvida=false` reabre, e `apagar_nota` remove de vez.

Os valores de `bloco`, `prioridade`, `estimativa` e `status` aceitam acento e
qualquer caixa: "Seguranca" e "seguranca" sao o mesmo bloco.

`sugerir_proximas` devolve o ranking do motor de priorizacao
(`backend/priorizacao.py`): score, `motivos` em frases prontas e alertas de
inversao de prioridade, inflacao de "alta" e trabalho parado. O calculo e um
modulo puro, entao a tela usa a mesma regra por `GET /priorizacao`, sem IA.
Todos os pesos estao no dict `PESOS`, no topo do modulo.

`ver_calibracao` compara a estimativa com a duracao real (`iniciada_em` ate
`concluida_em`, em dias corridos) das tasks concluidas, por classe e por
bloco. O veredito e `coerente`, `superestimada`, `subestimada` ou
`sem_dados` (amostra menor que `AMOSTRA_MINIMA`). O `validar_task` devolve
isso em `aviso_calibracao`, que informa e NAO reprova a task. As faixas estao
em `FAIXAS`, no topo de `backend/calibracao.py`.

`ver_perfil` junta a calibracao, a taxa de aceitacao por tipo de decisao, as
correcoes humanas mais comuns, as preferencias ativas e os
`padroes_candidatos` — habitos com pelo menos `MINIMO_OCORRENCIAS` registros e
`CONSISTENCIA_MINIMA` de consistencia que ainda nao viraram regra. Os dois
limiares estao no topo de `backend/perfil.py`.

Correcao humana entra sozinha: o MCP manda o header `X-Falange-Fonte: mcp` em
toda chamada, a tela nao manda. Quando uma task com `origem = ia` tem
estimativa, prioridade ou bloco alterados por uma chamada sem o header, o crud
grava uma `decisao` do tipo `ajuste_humano` com antes e depois.

`ver_autonomia` traz o nivel de cada acao (`perguntar`, `confirmar_em_lote`,
`automatico`) e se o historico ja permite subir: `JANELA` decisoes seguidas,
todas aceitas. Subir exige sim explicito do humano; descer e automatico
quando alguem discorda de algo feito no `automatico`. A assimetria e
proposital, e a tela so rebaixa. Apagar task ou nota nao esta no enum de
acoes: destrutivo nunca fica automatico.

`perguntas_ativas` (em `GET /configuracao`) liga e desliga as perguntas de
multipla escolha da IA. Desligado, ela decide sozinha e diz o criterio. Da
para alternar na tela ou pela tool `definir_configuracao`.

Toda task tem `prioridade` (alta/media/baixa, padrao media) e os marcos de
tempo `criada_em`, `atualizada_em`, `iniciada_em` e `concluida_em`.
`listar_tasks` devolve as mais prioritarias primeiro e aceita filtro por
`prioridade`.

Nenhuma tool levanta excecao para erro previsivel: devolve
`{"erro": "<frase>"}`. Quem le isso e um modelo, e uma excecao vira
`Error executing tool X` do lado do client, que nao diz o que corrigir.

`gerar_tasks_a_partir_de_arquivo` aceita um arquivo ou uma pasta e devolve
conteudo, estrutura extraida, o template e as tasks existentes. Pasta e
percorrida de forma recursiva (ate 60 mil caracteres), pulando `.git`,
`node_modules`, `.venv`, `__pycache__`, `.next`, `dist` e `build`, com
documentacao antes de codigo; a resposta traz `arquivos_lidos` e
`arquivos_ignorados` com o motivo de cada exclusao. Quem redige as
pre-tasks e a IA que chamou. `validar_task` aplica lint deterministico
(tamanho, enchimento, criterio de aceite, coerencia da estimativa,
duplicata) - nao depende do humor do modelo.

A leitura (de arquivo ou pasta) e limitada a `FALANGE_DOCS_ROOT` (`/app/exemplos` no
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

## Usar pelo Claude Code

Com a stack no ar, abra o projeto no Claude Code e use:

| Comando | O que faz |
|---|---|
| `/falange-gerar <arquivo>` | documentacao/codigo vira tasks: sugere, valida e so cria depois da sua aprovacao |
| `/falange-nova <descricao>` | uma task a partir de texto livre (entende "depois da #7") |
| `/falange-status [bloco\|pessoa]` | panorama: blocos, cadeias de bloqueio, sobrecarga (so leitura) |

Pedidos em texto livre tambem funcionam: o `CLAUDE.md` manda sempre usar as
tools do MCP, nunca banco ou codigo.

**Primeira vez nesta maquina:** rode `claude` nesta pasta (ou abra uma sessao
nova na extensao), aceite a confianca na pasta e aprove o servidor `falange`.
Sem isso o Claude Code ignora as permissoes de `.claude/settings.json` e o
servidor fica "Pending approval". `apagar_task` sempre pede confirmacao.

`/falange-gerar` so le arquivos e pastas dentro de `FALANGE_DOCS_ROOT`
(no `.mcp.json`, a raiz deste repo). Para gerar tasks da documentacao de outro projeto, aponte
essa variavel para ele.

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

Design final do frontend (o board atual e funcional, nao definitivo), RAG
com embeddings sobre a documentacao (V1 le a pasta inteira ate um limite),
gamificacao/war room, autenticacao e multi-usuario. `responsavel`
e texto simples de proposito - vira FK para usuario no V2.
