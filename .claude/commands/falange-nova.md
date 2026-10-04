---
description: Cria uma task do Falange a partir de uma descricao livre
argument-hint: <o que precisa ser feito>
---

Crie uma task no Falange a partir deste pedido:

> $ARGUMENTS

Use SOMENTE as tools do servidor MCP `falange`. Nao edite codigo nem acesse
o banco. Se o pedido estiver vazio, pergunte o que deve ser feito e pare.

## 1. Redigir

Monte os campos a partir do pedido:

- `titulo`: imperativo, 6 a 80 caracteres, sem ponto final.
- `descricao`: 40 a 800 caracteres. O que fazer e como saber que acabou.
  Termine com uma linha `Criterio de aceite: ...`.
- `estimativa`: PP (ate ~2h), P (ate ~1 dia), M (ate ~3 dias), G (mais que isso).
- `bloco`: frontend, backend, infra ou seguranca.
- `prioridade`: alta se trava outra task ou e pre-requisito de uma entrega
  proxima; baixa se pode esperar sem travar ninguem; media no resto. Se o
  pedido nao indicar nada, use media.
- `responsavel`: so se o pedido citar alguem.

Nao invente escopo que o pedido nao tem. Se faltar informacao essencial
(ex.: nao da para saber o bloco), pergunte antes de criar.

## Perguntar so quando ha duvida real

Chame `ver_configuracao` antes de redigir.

Com `perguntas_ativas` true, pergunte (AskUserQuestion, ou lista numerada se
ela nao estiver disponivel) quando:

- a prioridade for defensavel de duas formas (ex.: trava outra task, mas a
  entrega e distante);
- a estimativa ficar entre duas faixas e o lint nao resolver;
- uma task G puder virar duas entregas.

Com `perguntas_ativas` false, decida sozinho e diga em uma linha o que
escolheu e por que.

**Perguntar a toa e tao ruim quanto decidir errado.** Se o pedido ja da a
resposta, nao pergunte.


Se o pedido mencionar outra task ("depois da #3", "travada pela #5"), anote
para o passo 3.

## Estimar com os dados do time, nao com o chute de sempre

Chame `ver_calibracao` antes de redigir. Ela diz o que cada classe valeu na
pratica (`veredito`: coerente, superestimada, subestimada, sem_dados) no
projeto e por bloco. Prefira o veredito do BLOCO quando ele tiver amostra.

- `subestimada`: a classe costuma estourar a faixa; suba a estimativa.
- `superestimada`: costuma sair antes; desca.
- `sem_dados`: amostra pequena demais, estime como faria normalmente.

Quando a calibracao te fizer escolher diferente do que voce escolheria
sozinho, diga isso em uma linha, com o `n`. Ex.: "coloquei M e nao P porque
em infra P tem mediana de 3 dias (n=6)".

O `validar_task` tambem devolve `aviso_calibracao`. Ele NAO reprova a task:
e informacao para voce decidir, e vale mostrar ao dev quando aparecer.

## 2. Validar

Chame `validar_task`. Ele e a regra final: se ele discordar das regras
acima, vale ele.

- `precisa_de_ajuste`: corrija o conteudo resolvendo cada motivo e valide
  de novo, no maximo 2 vezes.
- Se ainda reprovar, mostre a versao e os motivos, pergunte como seguir e pare.

## 3. Criar

Com a task aprovada, chame `criar_task`. O pedido do usuario ja e a
autorizacao para criar.

Se houver dependencia, chame `marcar_bloqueio` com o `id` devolvido. Se
voltar `erro`, reporte.

## 4. Relatorio

Mostre `#id titulo [estimativa/bloco/prioridade]`, a descricao final e o bloqueio, se
houver. Se voce mudou algo relevante do pedido original, diga o que.

Lembre que ela aparece em http://localhost:3010 ao clicar em **Recarregar**.
