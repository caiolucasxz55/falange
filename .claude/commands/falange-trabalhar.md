---
description: O ciclo completo de uma task do Falange - escolher, implementar, commitar com #id e verificar
argument-hint: [id da task]
---

Trabalhe uma task do Falange de ponta a ponta. Id: `$ARGUMENTS` (opcional --
sem ele, escolha pelo `/falange-proximo`).

Use SOMENTE as tools do servidor MCP `falange` para mexer em task. O codigo
voce edita normalmente; o BACKLOG so pelas tools.

Este e o comando que fecha o circulo: a task sai do backlog, vira codigo,
vira commit, e volta como prova. Nenhum passo pula.

## 1. Escolher

**Com id:** `listar_tasks` e ache a task. Confira que ela nao esta
`bloqueada` -- se estiver, mostre `depende_de` e pergunte se o dev quer
atacar a dependencia em vez dela.

**Sem id:** rode o fluxo do `/falange-proximo` (coletar, 2 a 3 caminhos,
perguntar). Nao escolha sozinho se `perguntas_ativas` for true.

Antes de planejar, `ver_perfil` e respeite as `preferencias_ativas` como
regra do time.

## 2. Combinar o plano ANTES de escrever codigo

Leia os `criterios` da task em voz alta (no relatorio) e diga, para cada um,
**o que voce vai fazer para cumpri-lo**. Isso e o plano.

Se algum criterio nao der para cumprir como esta escrito -- vago, ou
impossivel -- diga agora, antes de comecar. Criterio ruim descoberto no fim
vira discussao sobre o que "valia", que e a conversa que a lista de
criterios existe para evitar.

Se a task for G, ofereca quebrar em duas antes de comecar.

## 3. Mover para em_andamento

`mudar_status(<id>, "em_andamento")`. So agora -- marcar antes de ter plano
enche o board de task "em andamento" que ninguem tocou.

## 4. Implementar

Trabalhe normalmente: leia o codigo em volta, siga a arquitetura do
`CLAUDE.md` (rota em `rotas/`, query em `repositorio/`, julgamento em
`dominio/`), escreva teste.

Se descobrir que a task e maior do que parecia, PARE e diga. Nao estique o
escopo em silencio -- a estimativa errada e informacao para a calibracao, e
esconder isso envenena o aprendizado do time.

Se descobrir um defeito que nao e desta task, anote para o passo 7. Nao
conserte de passagem: o commit fica com duas coisas dentro e a evidencia
deixa de apontar para uma entrega so.

## 5. Commitar citando a task

Rode os testes antes (`python -m pytest -q`). Falhando, nao commite.

O titulo do commit **tem** que citar a task:

```
feat: grafo de dependencias entre tasks (#42)
```

E por esse `#42` que `coletar_evidencias` vai achar o trabalho no passo 6.
Sem isso, a prova tem de ser registrada na mao, e o ciclo perde o que ele
tem de melhor.

Se o commit precisa de corpo, explique **por que**, nao o que -- o diff ja
diz o que.

## 6. Verificar

Rode o fluxo do `/falange-verificar <id>`: coletar os commits, ler os
diffs, veredito por criterio, registrar a prova, concluir conforme a
autonomia de `concluir_com_evidencia`.

Nao pule por achar que acabou de escrever o codigo e portanto sabe que
funciona. Esse e justamente o momento em que a verificacao tem valor: voce
e a parte interessada.

## 7. Fechar

- `#id` e o estado final, com o veredito por criterio.
- O que ficou `nao verificavel`, se algo ficou.
- Defeito ou duvida que apareceu no caminho: ofereca `/falange-nova` para
  virar task, ou `registrar_nota` para o que precisa de mais gente.
- `registrar_decisao` com `tipo: proxima_task` e o `rotulo` do caminho, se
  houve escolha no passo 1.
- Se a estimativa estourou ou sobrou, diga -- e isso que alimenta
  `ver_calibracao` para a proxima.
