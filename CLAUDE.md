# Falange

Organizador de tasks para times de dev. Backend FastAPI + Postgres, exposto a
IA pelo servidor MCP `falange` (`.mcp.json`), e uma tela de teste em Next.js
(`frontend/`, http://localhost:3010). Detalhes no `README.md`.

## Tasks: sempre pelo MCP

Criar, listar, editar, mudar status, bloquear ou apagar task e sempre pelas
tools do servidor `falange` (`mcp__falange__*`). Nunca pelo banco (`psql`,
SQL), por `curl` na API, nem editando codigo. Vale tambem para pedidos em
texto livre ("cria uma task pra X", "a #4 ja esta em andamento", "a #5 trava
a #6").

Antes de criar qualquer task, passe por `validar_task` e corrija o conteudo
ate aprovar.

Comandos prontos:

- `/falange-gerar <arquivo>`: documentacao ou codigo vira tasks. Sugere,
  valida e so cria depois da aprovacao do usuario.
- `/falange-nova <descricao>`: uma task a partir de texto livre.
- `/falange-status [bloco|responsavel]`: panorama, somente leitura.

As tools devolvem `{"erro": "..."}` em vez de falhar: leia a mensagem e
corrija a chamada. "Backend inacessivel" significa que a stack esta fora:
`docker compose up -d`.

## Codigo

- O MCP fala com o backend so por HTTP. `falange_mcp/` nao importa nada de
  `backend/` e nao conhece `DATABASE_URL`.
- Tool nova: funcao em `falange_mcp/tools.py` + citar em `TOOLS` no
  `falange_mcp/server.py`. Registre a permissao dela no
  `.claude/settings.json`: `allow` para leitura e escrita comum, `ask` se
  for destrutiva (como `apagar_task`).
- Portas nesta maquina: backend 8010, MCP SSE 8765, frontend 3010, Postgres
  5433 (8000, 3000 e 5432 sao de outros projetos).
