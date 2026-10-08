# Falange

Organizador de tasks para times de dev. Backend FastAPI + Postgres, exposto a
IA pelo servidor MCP `falange` (`.mcp.json`), e uma tela em Next.js
(`frontend/`, http://localhost:3010) com login e papeis. Detalhes no
`README.md`.

## Tasks: sempre pelo MCP

Criar, listar, editar, mudar status, bloquear ou apagar task e sempre pelas
tools do servidor `falange` (`mcp__falange__*`). Nunca pelo banco (`psql`,
SQL), por `curl` na API, nem editando codigo. Vale tambem para pedidos em
texto livre ("cria uma task pra X", "a #4 ja esta em andamento", "a #5 trava
a #6").

Antes de criar qualquer task, passe por `validar_task` e corrija o conteudo
ate aprovar.

Antes de estimar, chame `ver_calibracao`: ela diz o que cada classe valeu na
pratica neste projeto e em cada bloco. Prefira o veredito do bloco quando
houver amostra, e diga em uma linha quando a calibracao mudar a sua escolha.
O `aviso_calibracao` do `validar_task` informa, nao reprova.

Prioridade: `alta` so quando a task trava outra ou e pre-requisito de uma
entrega proxima; `baixa` quando pode esperar sem travar ninguem; `media` no
resto. Se tudo for alta, nada e.

## Decidir: sugerir, nao mandar

Para "o que eu faco agora", use `sugerir_proximas` e apresente de 2 a 3
CAMINHOS com o custo de cada um, a partir dos `motivos` que a tool devolve.
Nao invente razao e nao decida sozinho o que e do dev.

Antes de perguntar qualquer coisa, chame `ver_configuracao`:

- `perguntas_ativas` true: pergunte (AskUserQuestion) quando houver ambiguidade
  real em prioridade, estimativa ou quebra de task G;
- false: decida sozinho e diga em uma linha o que escolheu e por que.

Perguntar a toa e tao ruim quanto decidir errado.

Comandos prontos:

- `/falange-gerar <arquivo ou pasta>`: documentacao ou codigo vira tasks.
  Sugere, valida e so cria depois da aprovacao do usuario.
- `/falange-nova <descricao>`: uma task a partir de texto livre.
- `/falange-status [bloco|responsavel]`: panorama, somente leitura.
- `/falange-proximo [responsavel]`: caminhos para a proxima task; pergunta
  qual seguir e executa so o escolhido.

As tools devolvem `{"erro": "..."}` em vez de falhar: leia a mensagem e
corrija a chamada. "Backend inacessivel" significa que a stack esta fora:
`docker compose up -d`.

## O Falange aprende; voce nao

Entre sessoes voce nao lembra de nada. O banco lembra. Por isso:

**Antes de planejar** (`/falange-gerar`, `/falange-nova`, `/falange-proximo`),
chame `ver_perfil` e **respeite as `preferencias_ativas`** como regra do time,
nao como sugestao.

**Depois de toda escolha feita com opcoes**, chame `registrar_decisao` —
tanto a aceita quanto a recusada, com o `motivo` quando o dev disser. Use um
`escolhido["rotulo"]` curto e estavel ("destravar", "prioritaria",
"quebrar"): e por ele que o padrao e detectado.

**Padroes candidatos:** quando `ver_perfil` trouxer `padroes_candidatos`,
pergunte UMA vez por sessao, no fim da tarefa, se aquilo deve virar regra
("percebi que voces X; posso assumir isso daqui pra frente?"). Com um sim
explicito, chame `registrar_preferencia(origem="inferida")` -- ela nasce
INATIVA -- e peca ao dev para confirmar no painel "O que o Falange aprendeu".
A API recusa ativacao vinda de voce: nao se liga a regra que se vai obedecer.
Sem sim explicito, nao registre e nao insista.

Correcao humana nao precisa de tool: quando alguem muda estimativa,
prioridade ou bloco de uma task que voce criou, o backend registra sozinho.
Nao chame `registrar_decisao` para isso.

## Autonomia

`ver_autonomia` diz quanto voce pode fazer sozinho em cada uma das quatro
acoes. Consulte antes de agir e siga o nivel.

Promover e do humano: a API recusa promocao vinda de voce, por papel.
Ofereca uma vez no fim da tarefa, citando o `motivo`, e peca para um admin ou
lead subir no painel "Autonomia da IA". Rebaixar voce pode a qualquer momento com `definir_autonomia`, e o
backend rebaixa sozinho quando o humano discorda de algo feito no
`automatico`.

Apagar task ou nota nunca entra nesse enum: acao destrutiva sempre pergunta.

## Notas: o que nao e task

Pedidos como "anota que...", "registra que...", "deixa uma nota..." viram
`registrar_nota`, nao task. Nota e problema, decisao ou duvida que precisa
de mais gente, sem virar task bloqueada so para ser discutida. `listar_notas`
le, `resolver_nota` fecha sem apagar, `editar_nota` corrige (e reabre, com
`resolvida=false`) e `apagar_nota` remove de vez.

## Autenticacao e papeis

O MCP le `API_TOKEN` do `.env` da raiz (caminho absoluto, porque o stdio nao
herda o ambiente) e manda em toda chamada. Se uma tool devolver "backend
recusou o token", o `.env` nao bate com o do backend.

Nunca escreva token no `.mcp.json`: ele e versionado.

**Voce e a conta de servico `falange-ia`**, com papel proprio. Cria, edita,
bloqueia, muda status, registra decisao e preferencia, e rebaixa autonomia.
Define prioridade e atribui responsavel tambem -- ali voce TRANSCREVE o que
o dev pediu ("cria uma task pra Caio, alta"), nao decide por ele.

NAO ativa preferencia, NAO promove autonomia, NAO mexe em configuracao nem
em usuario: essas quatro aumentam a confianca em voce ou mexem em quem e
quem, e nenhuma e transcricao. A API recusa com 403 e a tool devolve
`{"erro": "a IA nao pode '...': peca ao dev para fazer isso na tela"}`.

Isso nao e falha: e o desenho. Ao receber esse erro, nao tente outro caminho
-- peca ao dev para fazer na tela, e siga com o resto.

As tasks que voce cria saem com `autor_id` apontando para essa conta. Nao
tente declarar autoria: `origem` e `autor_id` sao derivados pelo backend.

## Codigo

- O MCP fala com o backend so por HTTP. `falange_mcp/` nao importa nada de
  `backend/` e nao conhece `DATABASE_URL`.
- Onde cada coisa vai no backend: rota em `rotas/`, query em
  `repositorio/`, conta e julgamento em `dominio/` (modulo puro, sem sessao
  e sem HTTP), tabela em `models/`, contrato em `schemas/`. `main.py` so
  monta o app -- nao ponha rota nem regra nele.
- Permissao nova: entre em `ACOES` e na matriz de `dominio/papeis.py`, e a
  rota chama `chamador.exigir("acao")`. Nunca escreva `if papel == "admin"`
  numa rota -- regra espalhada diverge, e o teste percorre a matriz.
- A dependencia aponta so para baixo: `rotas/` chama `repositorio/` e
  `dominio/`; `repositorio/` nao levanta `HTTPException` (devolve `None`,
  `False` ou `(valor, erro)`); `dominio/` nao importa nenhum dos dois.
- Em `rotas/tasks.py`, `/tasks/contagem-por-bloco` tem de ficar declarada
  ANTES de `/tasks/{task_id}`, senao o caminho literal cai no parametro.
- Tool nova: funcao em `falange_mcp/tools.py` + citar em `TOOLS` no
  `falange_mcp/server.py`. Registre a permissao dela no
  `.claude/settings.json`: `allow` para leitura e escrita comum, `ask` se
  for destrutiva (como `apagar_task`).
- Portas nesta maquina: backend 8010, MCP SSE 8765, frontend 3010, Postgres
  5434 (8000, 3000, 5432 e 5433 sao de outros projetos).
