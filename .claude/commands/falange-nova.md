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

Se o pedido mencionar outra task ("depois da #3", "travada pela #5"), anote
para o passo 3.

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
