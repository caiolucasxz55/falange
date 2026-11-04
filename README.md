# Falange V2

Organizador de tasks para times de dev, onde a IA opera o quadro pelo MCP
e responde pelo que faz.

Backend FastAPI sobre Postgres, tela em Next.js com login e papeis, e um
servidor MCP em dois transportes. O que distingue o Falange de um board
comum e menos a lista de funcionalidades e mais o desenho em volta da IA:

- ela **nao conclui task dizendo que concluiu** -- precisa de evidencia
  ligada a cada criterio de aceite;
- ela **nao aumenta a propria confianca**: ativar preferencia, promover
  autonomia, mexer em configuracao e em usuario sao recusados por papel;
- ela **nao cria compromisso de entrega**: marco e de quem responde pela
  entrega;
- o que ela decide com opcoes vira **decisao registrada**, e dai o sistema
  aprende o padrao do time -- entre sessoes a IA nao lembra de nada, e o
  banco lembra.

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

O backend tem quatro camadas, e a dependencia so aponta para baixo:

    backend/
      main.py          <- monta o app: CORS, middlewares, routers. E so isso.
      middlewares.py   <- token e rate limit, antes de qualquer rota
      rotas/           <- HTTP: le o pedido, chama, escolhe o status
      repositorio/     <- banco: toda query mora aqui, uma por agregado
      dominio/         <- juizo: modulo puro, sem sessao e sem HTTP
      models/          <- tabelas (SQLAlchemy), um arquivo por agregado
      schemas/         <- contrato de entrada e saida (Pydantic)
      seguranca/       <- quem alcanca a API e o que cada lado pode fazer

`rotas/` nao sabe SQL e `repositorio/` nao sabe o que e um status HTTP: ele
devolve `None`, `False` ou `(valor, erro)` e quem traduz para 404 ou 409 e a
rota. `dominio/` nao conhece nenhum dos dois.

Regra do calculo: o que e juizo (ranking, limiares, alertas) mora em modulo
puro em `dominio/`, sem sessao e sem HTTP. A IA redige e conversa; o codigo
calcula e julga. A tela consome o mesmo resultado por endpoint.

Regra: o MCP nunca fala com o Postgres direto. Sempre via HTTP. Uma fonte
de verdade so, e os dois transportes ficam sendo cascas finas.

## Subir tudo (Docker)

    cp .env.example .env        # ajuste POSTGRES_PASSWORD
    docker compose up -d --build

| Servico | Host | Papel |
|---|---|---|
| `db` | `localhost:5434` | Postgres 18, volume `pgdata` |
| `migrate` | - | roda `alembic upgrade head` e sai |
| `backend` | `localhost:8010` | API FastAPI |
| `mcp` | `localhost:8765/mcp` | servidor MCP para o time (Streamable HTTP) |

Portas do host escolhidas para nao colidir com o que ja roda nesta maquina:
5432 e do Postgres nativo, 8000 e 8001 sao de outros projetos.

O `stdio` nao vira servico: por definicao e um subprocesso que o client
local sobe, nao um servidor que fica escutando.

O `backend` tem healthcheck e o `mcp` so sobe depois dele responder.
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

## Frontend

Tela minima em Next.js para ver o fluxo MCP -> backend. Detalhes em
`frontend/README.md`.

    cd frontend && npm install && npm run dev     # http://localhost:3010

O backend libera CORS so para as origens em `CORS_ORIGINS` (padrao
`http://localhost:3010`).

### A tela respeita o papel

`GET /eu` devolve o papel e a lista de acoes, e a tela esconde o que aquele
papel nao alcanca: um leitor nao ve formulario de task nem botao de apagar,
um dev nao ve "Promover" na autonomia, so admin ve o painel "Time".

Esconder **nao e autorizar**: a API recusa de todo jeito. Isto existe para
nao oferecer botao que ja se sabe que vai dar 403 -- a checagem de verdade
esta em `dominio/papeis.py`.

No modo de transicao (`EXIGIR_LOGIN=false`) a tela mostra um aviso "sem
login" e um link "entrar com uma conta": sem ele, o login ficaria
inalcancavel, porque `/eu` responde 200 e a tela nunca cairia no formulario.

## Projetos

Task, nota, decisao, preferencia, configuracao e autonomia pertencem a um
**projeto**. Usuario e sessao sao globais -- papel por projeto esta fora da
V2.

Existe para o Falange poder guardar o proprio backlog sem misturar com dado
de verificacao: sem isso, testar o sistema ponta a ponta cria e apaga linhas
no mesmo banco onde esta o trabalho real.

O projeto vai no header `X-Falange-Projeto: <slug>`. Sem o header, vale o
projeto `padrao`, que a migration 0008 cria e para onde ela move tudo o que
ja existia. Slug desconhecido da **404**, e nao "cai no padrao": escrever no
projeto errado por um typo seria pior que receber um erro.

Dois projetos nao se enxergam. Buscar uma task de outro projeto da 404 --
para quem pergunta de fora, ela nao existe. Ja relacionar coisas de projetos
diferentes (dependencia, nota apontando para task) da **409**: o pedido e
coerente, so cruza uma fronteira.

Calibracao, perfil, priorizacao, configuracao e autonomia sao calculados por
projeto. A IA ter ganhado autonomia num contexto nao diz nada sobre outro.

- **Tela:** seletor no cabecalho, lembrado no navegador (`localStorage`).
  Trocar recarrega a pagina de proposito: o projeto atravessa todos os
  paineis, e avisar um a um deixaria a tela misturando dois projetos por
  alguns instantes.
- **MCP:** a env `FALANGE_PROJETO` define em que projeto AQUELE servidor
  escreve, e vai no header em toda chamada. Vazia cai no padrao. Fica no
  `.mcp.json` por servidor, nao no `.env`: e o que separa o backlog real do
  sandbox descartavel. A tool `ver_projeto` responde onde a IA esta; criar
  projeto e so do admin, pela tela.
- **Papel:** `gerir_projetos` (listar e criar) e so de admin. Ver o projeto
  atual basta poder `ler`.
- Nao existe remocao de projeto: apagar levaria junto tudo o que pertence a
  ele.

## Dependencias entre tasks

Uma task pode esperar por **varias** outras, e `bloqueada` nao e um campo
guardado: e uma pergunta respondida na hora -- *esta task tem alguma
dependencia que ainda nao foi concluida?*

Antes era um ponteiro so (`task.bloqueada_por`), e o ponteiro mentia em dois
lugares. Primeiro cabia uma dependencia: a segunda sobrescrevia a primeira em
silencio. Depois concluir uma task tinha de **apagar** o bloqueio de quem
esperava por ela, e reabrir nao desfazia -- o estado derivado ficava para
tras do fato.

Agora as arestas vivem na tabela `dependencia` (`task_id` espera por
`depende_de_id`), e `mudar_status` nao toca em nenhuma: concluir ja libera
quem esperava, e reabrir volta a travar, sem nada para sincronizar.

Cada task sai da API com tres campos derivados:

| Campo | O que e |
|---|---|
| `depende_de` | de quem ela espera |
| `travando` | quem espera por ela |
| `bloqueada` | tem dependencia nao concluida |

Com grafo vem ciclo. `POST /tasks/{id}/dependencias` recusa auto-dependencia
e **qualquer** ciclo, inclusive o longo de varios passos (A espera B, B
espera C, e C tenta esperar A) -- a conta esta em `dominio/grafo.py`, modulo
puro, que tambem responde quem a conclusao de uma task destrava e qual a
origem de uma cadeia.

A tela conta `travando` a partir do que o **backend** devolve, nao do que ela
carregou: contar no navegador veria so a pagina atual, e o filtro de bloco ou
responsavel esconderia dependentes.

Remover e sempre de uma aresta especifica
(`DELETE /tasks/{id}/dependencias/{outra}`). Com N:N, "desbloquear" sem dizer
qual seria ambiguo.

## Criterio de aceite

O criterio de aceite ja era obrigatorio -- mas como uma **linha de texto**
dentro da descricao, exigida pelo lint da pre-task. Servia para a pessoa
ler, e so: nada no sistema sabia quantos criterios uma task tinha, nem
quais faltavam.

Agora cada criterio e uma linha da tabela `criterio`, de 1 a 5 por task,
10 a 200 chars cada. O teto nao e arbitrario: task que precisa de seis
criterios para ser explicada e duas tasks.

`criar_task` aceita `criterios: list[str]`, e toda task sai da API com
`criterios` montado junto de `depende_de` e `travando`.

### O que o lint recusa

Criterio tem de ser **observavel**: algo que da para olhar e dizer
"cumpriu" ou "nao cumpriu". O lint (`falange_mcp/template.py`) recusa
mecanicamente:

| Recusa | Exemplo |
|---|---|
| promessa de intencao | "funcionar bem", "o codigo fica mais limpo" |
| nada observavel | "a parte de backend da feature" |
| enchimento | "retorna 409, 422 e afins" |
| curto ou longo demais | "retorna" |
| repetido | o mesmo criterio duas vezes |

Aprova quando ha um verbo de observacao ("retorna", "aparece", "recusa"),
um numero ou um identificador tecnico: "o login com token vencido retorna
401" passa; "funcionar bem" nao.

Esse julgamento mora **so no MCP**, de proposito. E heuristica de prosa, e
reprovar o texto de um humano na tela por heuristica seria pior que deixar
passar. A API garante o que e estrutural: quantidade, tamanho e aparo.

### Onde o estado ainda nao existe

`cumprido_em` nasce nulo e nada na Fase E o preenche -- nem a tela. O
checklist do card **mostra**, nao marca: quem da um criterio por cumprido e
a evidencia, na Fase F. Clicar para atestar a si mesmo e exatamente o que a
evidencia veio substituir, entao o card desenha um quadradinho, nao um
`<input type="checkbox">` que convidaria ao clique sem efeito.

`evidencia_id` tambem nao existe ainda: uma coluna apontando para uma
tabela que nao foi criada nao e uma FK, e um inteiro solto esperando virar
uma. Entra na Fase F, junto da tabela que referencia.

### As tasks que ja existiam

A migration 0010 extrai das descricoes as linhas "Criterio de aceite: ..."
e **mantem o texto onde esta**: reescrever a descricao para tirar a linha
seria o upgrade editando conteudo que uma pessoa escreveu.

E melhor esforco, com limites assumidos: task sem a linha fica com zero
criterio (nao ha como inventar criterio para task antiga), bullet logo
abaixo do marcador vira um criterio por bullet, e texto acima de 200 chars
e cortado com reticencia. O "de 1 a 5" vale para o que se cria daqui pra
frente.

## Marcos: a entrega com data

A regra de prioridade sempre disse que `alta` vale quando a task "e
pre-requisito de uma **entrega proxima**". Mas nada no sistema sabia o que
era uma entrega, nem quando ela era -- quem decidia era a memoria de quem
estava olhando. O marco e o dado que faltava para essa regra.

Deliberadamente raso: um nome e uma data. Sem sprint, sem epico, sem
hierarquia. A task aponta para um marco ou nao aponta.

| Acao | Quem |
|---|---|
| criar, editar, fechar, apagar marco | admin e lead (`gerir_marcos`) |
| por uma task num marco | qualquer um que edite task, inclusive a IA |

A IA **nao cria marco**, e isso e desenho: um marco e um compromisso de
entrega com data, e compromisso nao e transcricao de pedido. Dizer de qual
entrega uma task faz parte, isso ela faz -- e transcricao, como `bloco`.

`data_alvo` e `Date`, nao `DateTime`: prazo de entrega e um dia, nao um
instante. Guardar hora traria fuso para uma conta de calendario, e "vence
as 23:59 de onde?" nao tem resposta boa num time distribuido.

Apagar um marco **nao apaga as tasks dele**: a FK e `SET NULL`, entao elas
so perdem o agrupamento. Apagar trabalho nao e o que alguem espera de
"remover a etiqueta".

### A previsao, com a conta exposta

`GET /marcos/previsao` devolve cada marco com um veredito -- `no_prazo`,
`em_risco`, `atrasado`, `sem_data` ou `concluido` -- e com a CONTA que o
sustenta: dias de trabalho restante, dias de calendario, e o detalhe por
classe de estimativa.

A conta exposta e o ponto. "Em risco" sem numero e palpite, e palpite de
software sobre prazo nao convence ninguem, com razao. Com a conta a vista,
quem discorda tem onde apontar.

O numero de cada classe vem da **calibracao do time** quando ha amostra, e
da faixa nominal quando nao ha -- a mesma calibracao que a IA consulta
antes de estimar. Se o painel usasse uma media propria, ele contradiria a
conversa sobre a mesma task, e ninguem saberia qual acreditar.

Sem amostra, usa o MAIOR valor da faixa, nao o meio: errar para o
pessimista avisa cedo; errar para o otimista avisa quando nao da mais
tempo de fazer nada.

**O que a previsao nao e:** ela soma a mediana de duracao de cada task
aberta, o que trata o time como se fizesse uma task por vez e nao tivesse
feriado nem reuniao. A alternativa seria modelar capacidade, paralelismo e
calendario -- e um modelo desses erra com mais confianca. A soma simples,
com a conta a vista, erra de um jeito que a pessoa percebe e corrige. Esta
dito na docstring de `dominio/previsao.py` para ninguem achar que e mais
do que e.

O limiar de risco e passar de **80%** do tempo restante. Nao e 100% porque
chegar raspando nao e "no prazo": e um aviso que chegou tarde demais para
alguem fazer algo a respeito.

### O peso de prazo na priorizacao

Task de marco que vence em ate **7 dias** ganha o mesmo peso de
`prioridade_alta` (30). Nao e coincidencia: a regra prometia que alta valia
para entrega proxima, entao o peso tem de bater com o que ela prometia.

Mais de uma semana nao pesa -- tudo de todo marco viraria urgente, e o peso
deixaria de distinguir qualquer coisa.

Junto vem o alerta `marco_em_risco`, quando a data esta perto e ainda ha
task aberta. Ele e mais simples que a previsao de proposito: repetir a soma
inteira ali faria duas contas de prazo que podem divergir.

### A pegadinha de ordem de rota, agora com guarda

`/marcos/previsao` tem de ser declarada ANTES de `/marcos/{marco_id}`,
senao o literal cai no parametro e vira 422. E a mesma armadilha de
`/tasks/contagem-por-bloco`.

Isso ja estava escrito em comentario e no `CLAUDE.md`, e mesmo assim
reapareceu na primeira rota nova -- comentario nao impede reordenacao.
`tests/test_ordem_de_rotas.py` varre o fonte de `backend/rotas/` e falha
quando um caminho literal e declarado depois de um parametrizado que o
cobre, dizendo qual mover para onde.

## Evolucao: o que o estado atual nao conta

As outras tabelas guardam o **estado atual**. Uma task diz que esta
concluida; nao diz quando saiu de aberta, quantas vezes voltou, nem quem a
moveu. Essa informacao existia e era jogada fora a cada escrita.

A tabela `evento` guarda cada mutacao de task, dependencia, evidencia e
nota, com `dados` em JSONB. Dai saem `GET /evolucao` e `resumo_periodo` --
nenhum dos dois da para calcular do estado atual, porque os dois sao sobre
a passagem do tempo.

### Nao e auditoria, e nao tenta ser

Sem assinatura, sem cadeia de hash, e o registro mora na mesma transacao do
que ele descreve: quem alcanca o banco altera os dois. Para contar a
evolucao do time isso basta. Para provar o que alguem fez contra a vontade
dessa pessoa, nao basta -- e dizer que basta seria pior que nao ter.

### Por que contar o evento, e nao o estado

| Pergunta | Olhando a task | Olhando o evento |
|---|---|---|
| task concluida, reaberta e concluida de novo | 1 entrega | 2 entregas, nas semanas certas |
| tempo de ciclo dela | o intervalo inteiro, incluindo o tempo parada pronta | cada ciclo medido separado |
| task apagada que foi entregue | some do grafico | continua contada |

O ultimo e por causa da FK: `evento.task_id` e **SET NULL**, nao CASCADE.
"A task #12 foi apagada" e justamente o evento que precisa sobreviver a
task #12 -- com CASCADE, ele se apagaria junto e o registro mais importante
seria o unico a sumir.

### O autor, sem passar por 20 assinaturas

O repositorio escreve o evento na MESMA transacao da mudanca -- e o jeito
de nao existir mudanca sem registro. Mas ele nao conhece o chamador, e
levar `autor_id` ate la exigiria o parametro em toda funcao de escrita.

`seguranca/contexto.py` resolve com um ContextVar preenchido por
`obter_chamador`. **So `autor_id`, e so para registro.** Autorizacao nunca:
permissao passa por `Chamador.exigir()`, explicito na rota, porque uma
checagem escondida num contextvar e impossivel de auditar lendo a rota -- e
e a rota que alguem le para saber o que ela protege.

### A tabela comeca vazia, e o endpoint diz isso

Nao da para reconstruir historia que nao foi guardada, e inventar eventos a
partir dos timestamps atuais produziria uma linha do tempo que parece real
e nao e -- pior que comecar do zero.

Com menos de 10 eventos, `/evolucao` devolve `aviso` em vez de desenhar um
grafico quase vazio. Grafico vazio parece "o time parou"; o aviso diz o que
de fato houve. O `/falange-resumo` e instruido a dizer isso **antes** de
qualquer numero, porque confundir "nao ha historico" com "nada aconteceu" e
a forma mais facil de o comando mentir.

### Semana comeca na segunda

Com semanas comecando em dias diferentes, duas leituras do mesmo periodo
dao numeros diferentes e ninguem sabe qual esta certo.

## Evidencia: concluir com prova

Uma task concluida pela IA precisa de prova, nao de afirmacao.

A assimetria que justifica isso: quando um dev diz "terminei", ele responde
por aquilo -- tem nome e historico no time. Quando a IA diz "terminei", nao
responde por nada; na sessao seguinte ela nao lembra de ter dito. Entao a
afirmacao dela nao vale como fato, e o que vale e o que da para conferir
depois de ela ter ido embora.

| Quem conclui | Precisa de prova? |
|---|---|
| admin, lead, dev **pela tela** | nao; a task fica marcada `concluida_sem_evidencia` |
| a conta de servico `falange-ia` | sim, em TODOS os criterios |
| a IA de alguem, **por token de conexao** | sim, mesmo com o papel humano do dono |

A terceira linha nao existia quando a regra foi escrita, e foi um buraco
real: o token de conexao resolve para o papel HUMANO do dono, entao olhar
so o papel deixava a IA concluir sem prova pelo caminho remoto -- que e o
caminho recomendado. `dominio/conclusao.exige_prova` passa a olhar tambem
a FONTE (`X-Falange-Fonte: mcp`), que o MCP manda em toda chamada.

O header e do cliente e da para omitir, e isso nao e brecha: um humano que
o tira esta fazendo pela API o que ja pode fazer pela tela. O header
APERTA quando esta presente; nunca afrouxa.

O humano concluir sem prova e de proposito, nao um furo: a pessoa responde
pelo que afirma, e travar o dev atras de um formulario faria o Falange
atrapalhar o trabalho em vez de organiza-lo. O preco e transparencia, nao
proibicao.

Para a IA, "todos os criterios com evidencia" nao basta: a task precisa TER
criterio. Sem essa segunda metade a regra se burla sozinha -- lista vazia
satisfaz "todos" por vacuidade, e quem escolhe os criterios e justamente
quem deveria obedecer a exigencia.

A recusa e **409, nao 403**: o papel ALCANCA a acao, o que falta e a prova.
403 mandaria a IA pedir permissao a um humano, quando o caminho certo e
registrar a evidencia.

### Os quatro tipos

| Tipo | Referencia | Conferivel por terceiros? |
|---|---|---|
| `commit` | sha (7 a 40 hex) | sim, com `git show` |
| `teste` | o teste que cobre o criterio | sim, rodando |
| `link` | URL | depende de quem le |
| `manual` | nao tem; o resumo e obrigatorio | nao, so confianca |

O schema valida o que da para validar sem o repositorio na mao: formato do
sha, referencia obrigatoria em `teste` e `link`, resumo obrigatorio em
`manual`. Evidencia de commit sem sha nao prova nada e ainda assim
destravaria a conclusao -- o que e pior que nao ter prova.

Se o commit EXISTE e se faz o que diz, quem confere e quem le. O Falange
nao tem como saber, e finge que nao sabe em vez de inventar um veredito.

### A convencao de commit

`#<id>` no titulo: `feat: grafo de dependencias (#42)`. E por isso que
`coletar_evidencias(42)` acha o trabalho.

O regex e `#42([^0-9]|$)`, nao `#42`: sem o grupo final, buscar a task 4
traria todo commit das tasks 40 a 49, e a evidencia da 4 ficaria cheia de
trabalho que nao e dela.

### Por que `coletar_evidencias` so existe no stdio

Ela roda `git` na maquina onde o SERVIDOR esta. No stdio isso e a maquina
do dev, e o repositorio e o dele. No SSE o processo roda num container,
longe de quem chamou -- ler o git de la examinaria um repositorio que nao e
de ninguem, ou nenhum.

Por isso ela recusa no SSE em vez de responder errado: uma lista vazia de
commits pareceria "nao ha evidencia", que e a conclusao OPOSTA a verdade
("nao da para olhar daqui").

O transporte e declarado pelo entrypoint ao montar o servidor
(`build_server(nome, transporte)`), nao adivinhado por nome nem por
variavel de ambiente -- para nao haver como ficar errado em silencio.

`subprocess` roda com lista de argumentos e `shell=False`, e o sha passa por
um `fullmatch` antes. E a unica parte do projeto que executa um binario
externo, entao vale a defesa em profundidade.

## Transportes do MCP

| Entrypoint | Transporte | Para que |
|---|---|---|
| `falange_mcp.stdio` | STDIO | a sua maquina, com o repositorio clonado |
| `falange_mcp.http` | Streamable HTTP (`/mcp`) | o time, sem repositorio |
| `falange_mcp.sse` | HTTP+SSE (`/sse`) | **legado**, para client que so fala SSE |

Streamable HTTP e o transporte atual do MCP: um endpoint so, que responde
JSON direto quando a resposta e curta e abre stream quando precisa, em vez
do par `GET /sse` + `POST /messages/`. O compose sobe ele.

O porteiro mora em `falange_mcp/porteiro.py` e e o MESMO nos dois: com uma
copia em cada entrypoint, a tendencia e uma receber a correcao e a outra
nao -- e a que ficar para tras vira a porta aberta de que ninguem lembra.

### Por que as tools continuam sincronas

O plano da V2 previa trocar `httpx` sincrono por `httpx.AsyncClient`, pela
razao de sempre: chamada bloqueante dentro de servidor async trava o event
loop.

Isso **nao se aplica a este SDK**. O MCP roda funcao de tool sincrona em
thread separada (`mcp/server/mcpserver/utilities/func_metadata.py`, a
chamada `anyio.to_thread.run_sync`), entao o `httpx.request` das tools nao
bloqueia o loop. Converter as 36 tools para async seria churn sem ganho --
e ainda obrigaria a reescrever o wrapper de credencial, que e onde mora a
parte delicada.

Isto esta escrito aqui porque a proposta vai voltar: ela parece obviamente
certa ate alguem abrir o SDK.

## Conectar o MCP sem ter o repositorio

Antes disto, ligar a IA no Falange exigia o repositorio clonado -- e quem
entrava pelo SSE usava as credenciais DO SERVIDOR, nao as proprias. Duas
pessoas no mesmo SSE eram a mesma conta para o backend: `autor_id`, papel e
projeto saiam todos errados. A V2 construiu identidade por pessoa, e o MCP
a descartava na porta.

O token de conexao fecha isso. A pessoa gera o dela, cola num `.mcp.json` e
conecta **como ela mesma**.

### O formato, e por que ele tem um prefixo publico

    flg_<prefixo>_<segredo>

| Pedaco | Onde fica | Para que |
|---|---|---|
| `flg_` | no token | scanner de segredo vazado reconhecer |
| prefixo | banco, em CLARO, com indice unico | achar a linha em O(1) |
| segredo | so o sha256 no banco | a credencial de fato |

O prefixo em claro e o que torna a validacao viavel: sem ele, conferir um
token exigiria hashear contra TODAS as linhas da tabela. Ele tambem e o que
a tela mostra na lista -- da para reconhecer qual token e qual sem revelar
nenhum.

**sha256 e nao argon2**, pela mesma razao que o refresh da sessao usa
sha256: o segredo tem 256 bits de entropia, entao nao ha dicionario para
percorrer nem senha fraca para proteger. argon2 existe para encarecer
ataque a segredo ADIVINHAVEL; aqui ele so custaria ~100ms por request, e
este token e conferido em TODA chamada do MCP.

### Quatro credenciais, um header

`Authorization: Bearer` carrega agora quatro coisas, e cada uma e resolvida
em `seguranca/dependencias.py`:

1. JWT de quem fez login (a tela);
2. token de conexao `flg_...` (o MCP de quem nao tem o repo);
3. token compartilhado + `X-Falange-Fonte: mcp` (a conta `falange-ia`);
4. token compartilhado sem header (a tela antes de haver login).

O middleware aceita o token de conexao **so pelo formato** -- ele nao tem
sessao de banco para conferir o hash. Isso e seguro porque toda rota que
faz algo depende de `obter_chamador`, que resolve o token de verdade e
levanta 401. As unicas rotas sem `obter_chamador` sao `/health`, o login e
o renovar, e as duas ultimas autenticam por conta propria.

Isso nao e confianca no comentario: `tests/test_token_mcp.py` varre o fonte
de `backend/rotas/` e falha se o conjunto de rotas sem `obter_chamador`
mudar. Rota nova sem ele seria alcancavel com um token inventado.

### O painel "Conectar sua IA"

Na barra lateral da tela. A pessoa da um nome ao token ("meu notebook"),
opcionalmente um prazo em dias, e recebe de volta duas coisas: o token e o
`.mcp.json` **pronto para colar**, com o endereco do SSE e o token dentro.
O que ela precisa fazer e copiar, nao entender.

O segredo aparece UMA vez, num aviso ambar, e o painel nao o guarda em
lugar nenhum -- nem em `localStorage`. Guardar para "poder ver depois"
desfaria o ponto de so mostrar uma vez.

A lista mostra nome, prefixo e `ultimo_uso_em`. Token **nunca usado**
aparece marcado como tal, de proposito: costuma ser o que a pessoa gerou e
perdeu, e e o candidato obvio a revogar. Revogar pede confirmacao e diz o
efeito ("a IA conectada por ele para de responder na proxima chamada").

O endereco do SSE e montado com o host de quem esta OLHANDO a tela
(`window.location.hostname`), nao com `localhost`: quem abre o Falange de
outra maquina da rede precisa do endereco que funciona para ela.

### O que o token NAO faz

- **Nao congela permissao.** O papel continua lido do banco a cada
  request, como no JWT: rebaixar alguem vale no request seguinte.
- **Nao amplia nada.** Ele vale o que o papel do dono vale. Um `leitor`
  com token conecta e so le.
- **Nao sobrevive ao corte de acesso.** Desativar, rebaixar ou cortar as
  sessoes de alguem agora revoga os tokens de MCP dela tambem. Antes o
  corte pegava so a sessao da tela -- e um notebook perdido tem o
  `.mcp.json` dentro dele, que e exatamente o caso que esse corte existe
  para resolver.
- **Nao e da conta de servico.** `falange-ia` ja entra pelo token
  compartilhado; um token de conexao apontando para ela seria credencial
  sem dono humano para revogar. A rota recusa com 403.

### Como a tool sabe quem chamou

Esta e a parte que nao e obvia, e o comentario em `falange_mcp/credencial.py`
existe para ninguem "simplificar" de volta.

A ideia obvia -- um middleware ASGI que le o header e guarda num
`ContextVar` -- **nao funciona no SSE**. O `POST /messages/` nao executa a
tool: ele valida, empurra a mensagem para um stream de memoria e responde
202. Quem executa e a task de longa duracao do `GET /sse`, que e outro
contexto async, e `ContextVar` nao atravessa task criada por fora. O valor
guardado no POST chegaria vazio.

O que o SDK carrega e o `Request` do POST, anexado a mensagem
(`ServerMessageMetadata(request_context=request)`). Entao a credencial e
lida no unico ponto que ve as duas coisas: o wrapper `_com_credencial` em
`falange_mcp/server.py`, que recebe o `Context` da chamada e preenche o
`ContextVar` em volta da funcao.

O wrapper existe para isso nao virar um parametro em 34 assinaturas de
tool. Ele ganha um `ctx: Context` que a tool nao tem; o SDK detecta pela
anotacao, injeta, e ESCONDE do schema -- a assinatura que a IA ve continua
sendo a da funcao original.

Duas coisas precisam ser remontadas a mao no wrapper, por motivos
diferentes: `__signature__`, porque `functools.wraps` copia `__wrapped__` e
o `inspect.signature` seguiria por ele; e `__annotations__`, porque a
deteccao do SDK usa `typing.get_type_hints`, nao a assinatura. Sem a
segunda, `ctx` vaza para o schema de TODAS as tools e nunca e injetado --
foi o que aconteceu na primeira versao. `tests/test_credencial.py` prende
as duas.

### Sem credencial, no SSE, nao se fala com o backend

`credencial.atual()` cai no `API_TOKEN` do servidor **so no stdio**, onde o
processo e do dev e a conta de servico e quem fala de fato.

No SSE o fallback e proibido por desenho. Ali ele significaria "nao sei
quem esta chamando, entao vou falar como a conta de servico" -- exatamente
o furo que esta fase veio fechar. O porteiro ja barra quem chega sem token,
mas depender so dele deixaria a identidade compartilhada a UM afrouxamento
de distancia, sem erro nenhum aparecer. Sem credencial no SSE, a chamada
sai sem `Authorization` e leva 401. Barulhento, e e o que se quer.

### O projeto vem do token

`obter_projeto` passa a olhar, nesta ordem: o token de conexao, o header
`X-Falange-Projeto`, e o `padrao`.

O token vem primeiro porque quem conecta de fora nao tem um `.mcp.json`
nosso para definir `FALANGE_PROJETO` -- cair no `padrao` escreveria no
projeto errado em silencio, que e o erro que os projetos resolveram com 404
em slug desconhecido. O projeto foi escolhido quando o token nasceu.

### O segredo sai uma vez

`POST /eu/tokens-mcp` e o unico lugar do sistema que devolve o segredo em
claro, e so na criacao. `TokenMCPCriado` e uma classe SEPARADA de
`TokenMCPOut` de proposito: assim nao ha como o campo escapar numa
listagem por alguem reaproveitar o schema -- ele simplesmente nao existe
no outro.

Perdido, o caminho e revogar e gerar outro. Revogar preenche
`revogado_em` e nao apaga a linha, como na sessao: saber que o token
existiu e foi cortado vale mais que o espaco.

### O que a IA nao pode desfazer

Nao existe `apagar_evidencia_propria`. A IA registra a propria prova; deixar
que ela tambem a apagasse daria a ela como apagar o rastro do que fez.
Apagar evidencia exige a permissao ampla de apagar.

`concluir_com_evidencia` e o valor novo no enum de autonomia, nascendo em
`perguntar`. Nao tem tipo de decisao, entao nunca promove sozinho -- e
desejavel: o que autorizaria confiar nela nao e um historico de escolhas
aceitas, e um humano ter CONFERIDO a prova. Essa promocao e na mao.

## Ambiente de teste

Um segundo backend, com banco proprio, para verificacao ponta a ponta nao
tocar o backlog real:

    docker compose --profile teste up -d

Sobe `db-teste` (Postgres em **tmpfs** -- mora em RAM e some quando o
container para), `migrate-teste` (migrations + semeia o projeto `sandbox`) e
`backend-teste` na **8011**, ao lado da 8010 do real.

Cada subida comeca limpa. Nao e so conveniencia: banco de teste que persiste
vira banco de teste sujo, e ai ninguem confia no resultado.

O banco de teste nasce sem conta humana, entao o `API_TOKEN` vale como admin
ali (ver "Primeiro admin"). E o que deixa a verificacao rodar sem criar
usuario antes de cada rodada.

**Cuidado com o `down`.** O `down` do Compose e do PROJETO inteiro, nao do
perfil: `docker compose --profile teste down` derruba tambem o backend real.
O dado nao se perde (o banco real esta em volume nomeado, e `down` sem `-v`
nao apaga volume), mas a stack para. Para derrubar so o teste, nomeie os
servicos:

    docker compose down db-teste migrate-teste backend-teste

## Configuracao

Cada pacote tem a sua, lida do `.env` ou de variaveis de ambiente:

| Arquivo | Le |
|---|---|
| `backend/config.py` | `DATABASE_URL`, `LIMITE_SOBRECARGA`, `CORS_ORIGINS` |
| `falange_mcp/config.py` | `BACKEND_URL`, `FALANGE_DOCS_ROOT`, `FALANGE_REPO_ROOT`, `MCP_SSE_HOST`, `MCP_SSE_PORT` |

O MCP nao conhece `DATABASE_URL` de proposito: nao tem como falar com o
banco nem por engano.

## Tools

| Tool | Escreve no banco? |
|---|---|
| `criar_task` | sim (com os criterios de aceite, no mesmo commit) |
| `listar_tasks` | nao |
| `editar_task` | sim (alteracao parcial) |
| `apagar_task` | sim |
| `adicionar_dependencia` | sim (recusa ciclo, inclusive longo, e auto-dependencia) |
| `remover_dependencia` | sim (solta de UMA; as outras ficam) |
| `mudar_status` | sim (nao mexe em dependencia: `bloqueada` e derivada) |
| `contar_tasks_por_bloco` | nao |
| `verificar_sobrecarga` | nao |
| `gerar_tasks_a_partir_de_arquivo` | **nao** - aceita arquivo ou pasta; so sugere, para voce revisar |
| `validar_task` | nao (recusa criterio que so promete intencao) |
| `coletar_evidencias` | **nao** - le o git local; so no stdio |
| `ver_diff_do_commit` | **nao** - le o git local; so no stdio |
| `registrar_evidencia` | sim (liga a prova aos criterios) |
| `listar_evidencias` | nao |
| `apagar_evidencia` | sim (criterio volta a "nao verificado") |
| `ver_evolucao` | nao (throughput, ciclo e marcos) |
| `resumo_periodo` | nao (o que mudou, travou e esta em risco) |
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
(`backend/dominio/priorizacao.py`): score, `motivos` em frases prontas e alertas de
inversao de prioridade, inflacao de "alta" e trabalho parado. O calculo e um
modulo puro, entao a tela usa a mesma regra por `GET /priorizacao`, sem IA.
Todos os pesos estao no dict `PESOS`, no topo do modulo.

`ver_calibracao` compara a estimativa com a duracao real (`iniciada_em` ate
`concluida_em`, em dias corridos) das tasks concluidas, por classe e por
bloco. O veredito e `coerente`, `superestimada`, `subestimada` ou
`sem_dados` (amostra menor que `AMOSTRA_MINIMA`). O `validar_task` devolve
isso em `aviso_calibracao`, que informa e NAO reprova a task. As faixas estao
em `FAIXAS`, no topo de `backend/dominio/calibracao.py`.

`ver_perfil` junta a calibracao, a taxa de aceitacao por tipo de decisao, as
correcoes humanas mais comuns, as preferencias ativas e os
`padroes_candidatos` — habitos com pelo menos `MINIMO_OCORRENCIAS` registros e
`CONSISTENCIA_MINIMA` de consistencia que ainda nao viraram regra. Os dois
limiares estao no topo de `backend/dominio/perfil.py`.

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
porque o `mcp` e o que fica exposto ao time.

## Autenticacao

Dois segredos no `.env` (fora do git):

| Variavel | Protege | Quem apresenta |
|---|---|---|
| `API_TOKEN` | a API do backend | o MCP local, e o proxy do frontend |
| `JWT_SEGREDO` | assina o access token do login | o backend (ninguem apresenta) |

O **servidor MCP remoto (SSE) nao tem segredo em arquivo**. A porta dele e
fechada pelo token de conexao de cada pessoa (`flg_...`), que mora no banco
e e revogavel na tela. O antigo `SSE_TOKEN` saiu: era um segredo unico para
todo o time, e quem passava por ele agia com as credenciais do SERVIDOR --
duas pessoas conectadas eram a mesma conta para o backend.

`JWT_SEGREDO` precisa de pelo menos 32 caracteres e o backend RECUSA subir
com menos: HMAC-SHA256 com chave curta e fraca (RFC 7518). Vazio desliga o
login, e `/sessao` responde 503. Trocar o valor desloga todo mundo.

Vazio = porta aberta, e o backend avisa no log ao subir. Isso so e aceitavel
em dev local. Gere com:

    python -c "import secrets; print(secrets.token_urlsafe(32))"

`/health` responde sem token, para o healthcheck do docker.

**Por que dois segredos:** quem alcanca o SSE usa as credenciais do servidor
para falar com o backend. Proteger so o backend nao protegeria nada: a porta
exposta precisa do porteiro dela.

**O frontend nao guarda segredo.** O navegador chama `/api/...`, uma rota do
proprio Next (`frontend/app/api/[...caminho]/route.ts`) que injeta a
credencial no servidor e repassa. Qualquer `NEXT_PUBLIC_` acabaria no bundle,
visivel para quem abrisse a pagina. Como o caminho e a mesma origem, o
frontend tambem deixou de depender de CORS.

O cookie so recebe `Secure` quando a requisicao chega por HTTPS (ou com
`x-forwarded-proto: https`, atras de um proxy que termina TLS). Amarrar isso
ao modo de producao quebrava `npm start` sobre http: o cookie saia `Secure`,
nunca voltava, e o login respondia 201 com tudo depois dando 401. Em
`http://localhost` o navegador disfarca -- ele trata localhost como contexto
seguro --, mas num endereco de rede a sessao morria calada.

Com login, esse proxy guarda o access e o refresh da pessoa em cookies
**HttpOnly**: o JavaScript da pagina nao os alcanca, entao um XSS na tela nao
rouba a sessao, e o `POST /sessao` volta ao navegador SEM os tokens. O proxy
tambem trata o 401 de access vencido sozinho -- renova com o refresh, repete
o pedido e grava os cookies novos -- para a pessoa nao ser deslogada a cada
15 minutos. Em producao o cookie recebe `Secure`; em dev local ele fica de
fora, senao o navegador descarta o cookie em `http://` e o login "funciona"
sem nunca logar.

### O que a API trava sozinha

O token diz quem pode usar; estas regras dizem o que cada lado pode fazer:

- **`origem` da task sai do header**, nunca do corpo. Autoria da IA nao e
  declaravel pelo cliente, senao daria para envenenar calibracao e perfil.
- **Promover autonomia e ativar preferencia exigem papel.** A IA pode
  propor; quem sobe a confianca e admin ou lead. Antes isso dependia do
  `ask` no `.claude/settings.json`, que e configuracao do CLIENTE e nao
  protege a API; depois passou a depender do header; hoje e papel.
- **Descer confianca e livre** para quem trabalha, inclusive para a IA.
- **Tamanhos com teto**: descricao 5000 chars, JSON de decisao 4000,
  arquivo lido 1 MB. Sem isso, Text e JSONB aceitam o que vier.
- **Limite de requisicoes** por cliente por minuto (`LIMITE_POR_MINUTO`,
  padrao 300; 0 desliga). E em memoria: morre no restart, nao e compartilhado
  entre replicas, e atras do proxy do frontend o time conta como um cliente
  so.

### Identidade por pessoa e papeis

O token acima diz "este cliente pode usar a API". Quem e voce vem do login.

**Login:** `POST /sessao` troca email e senha por um par de tokens. O
**access** e um JWT curto (`JWT_MINUTOS`, padrao 15) e o **refresh** e um
texto opaco guardado no banco -- so o hash dele. A senha usa argon2id.

Por que os dois: JWT nao revoga. Assinatura valida vale ate expirar, entao
logout, usuario removido ou papel rebaixado continuariam valendo pelo resto
da validade. Com a tabela `sessao`, a API confere a cada request se a sessao
ainda vale, e **o papel vem do banco, nao do token** -- rebaixar alguem tem
efeito no request seguinte. `POST /sessao/renovar` gira o refresh: um refresh
roubado vale uma vez so.

**Os quatro papeis humanos** sao uma escada, e `dominio/papeis.py` tem a
matriz inteira (`GET /eu` devolve o que o papel alcanca, para a tela nao
desenhar botao que vai dar 403):

| | admin | lead | dev | leitor |
|---|---|---|---|---|
| ler | sim | sim | sim | sim |
| criar e editar task | sim | sim | sim | - |
| mudar status, bloquear | sim | sim | sim | - |
| definir prioridade | sim | sim | - | - |
| atribuir responsavel | sim | sim | so a si | - |
| apagar task e nota | sim | sim | so as suas | - |
| promover autonomia, ativar preferencia | sim | sim | - | - |
| configuracao da plataforma | sim | - | - | - |
| gerir usuarios | sim | - | - | - |

Duas folgas deliberadas, para a regra nao virar burocracia: gravar a
prioridade PADRAO nao conta como "definir prioridade" (senao um dev nao
abriria task), e atribuir a SI MESMO nao conta como "atribuir responsavel"
(pegar trabalho e diferente de distribuir).

**`falange-ia` e o quinto papel**, e fica fora da escada: e a conta de
servico que o MCP usa, sem senha, que entra pelo `API_TOKEN`. E o que torna
as travas regra de papel em vez de checagem de header.

Ela apaga como um dev (so o que criou), mas define prioridade e atribui
responsavel como um lead -- de proposito: ali ela transcreve o pedido do
dev, nao dirige ninguem. O que ela nao tem e o que aumentaria a confianca
nela (ativar preferencia, promover autonomia) ou mexeria em quem e quem
(configuracao, usuarios). A isencao de "atribuir a si mesmo" nao a alcanca,
porque o `nome` dela e "Falange IA": sem a permissao ampla, o parametro
`responsavel` das tools falhava em todo caso.

**Autor e responsavel viraram fato.** `task.autor_id`, `task.responsavel_id`,
`nota.autor_id` e `decisao.autor_id` apontam para `usuario`. As colunas de
texto ficam, e nao sao legado: sao o rotulo de quem nunca virou conta.

`task.autor_id` e `decisao.autor_id` saem de quem fez a chamada: ali o par
nao conflita, porque o texto ao lado (`responsavel`) e outro conceito.

`task.responsavel_id` e `nota.autor_id` sao resolvidos a cada escrita a
partir do texto, com a mesma regra do backfill da migration 0007: liga quem
casa por nome (ignorando caixa e espaco), e fica NULL para nome solto. Fica
NULL tambem quando DUAS contas tem o mesmo `nome` -- a coluna nao e unica, e
escolher uma no palpite gravaria na pessoa errada; ai o texto segue sendo o
unico registro, que e o que ele existe para ser.

Na nota isso importa porque texto e id sao o MESMO conceito: enquanto
`autor_id` guardava quem chamou a API, uma nota escrita pelo MCP em nome da
Marina saia assinada "Marina Alves" com o id da conta de servico. Quem esta
logado assina a propria nota sempre -- aceitar o nome do corpo deixaria
qualquer um assinar como outra pessoa.

**Nao existe DELETE de usuario.** Apagar deixaria as tasks e decisoes da
pessoa apontando para ninguem. `PATCH /usuarios/{id}` com `ativo: false`
corta o acesso na hora e preserva o historico, e
`DELETE /usuarios/{id}/sessoes` derruba so as sessoes (o caso do notebook
perdido). O ultimo admin ativo nao pode se rebaixar nem se desativar.

**Primeiro admin (bootstrap):** num banco **sem nenhuma conta humana**, quem
chega com o `API_TOKEN` e sem o header do MCP e tratado como admin sem login.
Serve para criar a primeira conta por `POST /usuarios`.

Essa brecha **fecha sozinha na primeira conta criada**: dali em diante o
token compartilhado, sozinho, nao identifica ninguem e leva 401. Nao e zelo
-- enquanto ela ficava aberta, qualquer pessoa escalava privilegio apagando
o proprio cookie de sessao no devtools, porque a tela caia no token
compartilhado e o token compartilhado era admin. `HttpOnly` nao protege
disso: ele impede o JavaScript de LER o cookie, nao a pessoa de apaga-lo.

`EXIGIR_LOGIN=true` fecha a brecha de uma vez, inclusive no banco vazio; ai
o primeiro admin tem de ser criado por fora da API. O MCP nao e afetado em
momento nenhum: ele manda o header e e atendido como a conta de servico.

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
| `/falange-verificar <id>` | veredito por criterio, com a prova citada; conclui conforme a autonomia |
| `/falange-trabalhar [id]` | o ciclo inteiro: escolher, implementar, commitar com `#id`, verificar |
| `/falange-resumo [dias]` | o que mudou, travou e esta em risco no periodo (so leitura) |

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
- **`wslrelay` travado no Windows.** O container fica `healthy` (o
  healthcheck roda DENTRO dele, em `127.0.0.1`) e nada responde do host:
  requisicao morre em timeout, sem log no backend. O culpado e um processo
  `wslrelay` do Docker Desktop segurando o IPv4 loopback da porta enquanto
  o Docker escuta em `::`. Reiniciar o Docker Desktop NAO resolve; matar o
  processo resolve, e ele e recriado sozinho:

  ```powershell
  Get-NetTCPConnection -LocalPort 8010 -State Listen |
    Where-Object { $_.LocalAddress -eq '127.0.0.1' } |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
  ```

  Sintoma que confunde: `docker compose ps` diz "healthy", entao a suspeita
  cai no codigo. Se o backend nao tem log NENHUM da sua requisicao, ela nao
  chegou -- o problema esta antes dele.

## Fora do escopo

Entregue na V2: autenticacao por pessoa, papeis e identidade de autor.

Ainda fora: RAG com embeddings sobre a documentacao (hoje le a pasta inteira
ate um limite), gamificacao/war room, convite por email e recuperacao de
senha (um admin cria a conta e entrega a senha).
