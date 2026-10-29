---
description: Verifica uma task do Falange criterio por criterio, com a prova citada, e conclui conforme a autonomia
argument-hint: <id da task>
---

Verifique a task `$ARGUMENTS` do Falange: um veredito POR CRITERIO, cada um
com a prova citada.

Use SOMENTE as tools do servidor MCP `falange`. Se o argumento estiver
vazio, pergunte qual task e pare.

A regra que da sentido a este comando: **voce nao conclui task dizendo que
concluiu.** A API recusa com 409 enquanto algum criterio estiver sem
evidencia. Este comando existe para a prova ser real, nao para destravar o
status.

## 1. Ler a task

1. `listar_tasks` e ache a task pelo id (ou `sugerir_proximas` se precisar
   de contexto). Guarde os `criterios`: id, texto e `evidencia_id`.
2. `ver_autonomia` - o nivel de `concluir_com_evidencia` manda no passo 5.
3. `listar_evidencias(<id>)` - o que ja foi registrado antes.

Se a task nao tiver criterio nenhum, PARE. Sem criterio nao ha o que
verificar, e a API nao vai deixar voce concluir. Diga isso e ofereca
escrever os criterios com `editar_task`, para o dev aprovar.

## 2. Coletar a prova

1. `coletar_evidencias(<id>)` - os commits que citam `#<id>`.
2. Para cada commit relevante, `ver_diff_do_commit(<sha>)`. **Leia o diff.**
   O titulo do commit nao e prova de nada: "feat: valida token (#42)" pode
   ser um commit que so mexeu no README.
3. Rode os testes que cobrem o criterio, quando houver
   (`python -m pytest tests/test_x.py -q`). O teste que PASSA e a prova mais
   forte que existe aqui, porque qualquer um reproduz.

Se `coletar_evidencias` devolver zero commits, nao conclua que o trabalho
nao foi feito: pode ser que o titulo nao siga a convencao `#<id>`. Procure
por outro caminho (`git log` pelos arquivos do assunto) e diga o que fez.

## 3. Um veredito por criterio

Para cada criterio, escolha UM:

| Veredito | Quando |
|---|---|
| **cumprido** | ha prova no codigo, no teste ou no diff, e voce leu |
| **nao cumprido** | a prova existe e mostra que NAO atende |
| **nao verificavel** | nao ha como conferir daqui |

`nao verificavel` nunca vira `cumprido` por inferencia. Criterio de tela
("o card mostra o checklist") sem screenshot nem teste de componente e NAO
VERIFICAVEL, mesmo que voce tenha escrito o codigo e ele pareca certo. "Eu
escrevi, logo funciona" e exatamente a afirmacao que a evidencia veio
substituir.

Apresente assim, uma linha por criterio:

```
#1 cumprido        "retorna 409 no ciclo"
   -> tests/test_grafo.py::test_recusa_ciclo_longo passa (28 testes no modulo)
#2 nao verificavel "o card mostra o checklist"
   -> codigo em TaskCard.tsx:188, mas nao ha teste de componente nem print
```

## 4. Registrar a prova

Para cada criterio **cumprido**, `registrar_evidencia` com:

- `tipo`: `commit` (referencia = sha), `teste` (referencia = o teste, ex.
  `tests/test_grafo.py::test_recusa_ciclo_longo`), `link` ou `manual`;
- `resumo`: o que essa prova mostra, em uma frase;
- `criterio_ids`: os ids que ESTA prova cumpre. Uma prova pode cumprir
  varios -- um commit que fecha tres criterios e uma evidencia, nao tres.

Nao registre nada para `nao cumprido` nem para `nao verificavel`. Uma
evidencia registrada sem conferencia e pior que a ausencia dela: ela
destrava a conclusao e ainda parece auditada.

Se o criterio e verdade mas so um humano pode atestar (olhou a tela e
funciona), o tipo e `manual` e o `resumo` e obrigatorio -- e peca ao dev
para confirmar antes de registrar. Nao assine no lugar dele.

## 5. Concluir, conforme a autonomia

So se TODOS os criterios ficarem `cumprido`. Com qualquer um `nao
cumprido` ou `nao verificavel`, a task NAO fecha: diga o que falta e pare.

O nivel de `concluir_com_evidencia` manda:

- `perguntar` (o padrao): mostre o veredito e pergunte se pode concluir.
  **Termine a sua vez e espere.**
- `confirmar_em_lote`: conclua e mostre UM resumo para o dev aprovar ou
  mandar desfazer.
- `automatico`: conclua e reporte.

Ai `mudar_status(<id>, "concluida")`. Se vier 409, a prova nao esta
completa: leia a mensagem, ela diz qual criterio falta.

Se `pode` for true em `ver_autonomia`, ofereca a promocao UMA vez, no fim,
citando o `motivo`, e peca ao dev para subir no painel "Autonomia da IA". A
API recusa promocao vinda do MCP.

## 6. Fechar

- O veredito por criterio, com a prova citada.
- O que ficou `nao verificavel` e o que faria dele verificavel (um teste,
  um print, alguem olhando).
- Se achou defeito no caminho, ofereca `/falange-nova` para ele virar task,
  ou `registrar_nota` se for duvida que precisa de mais gente. Nao crie
  task sozinho aqui.
