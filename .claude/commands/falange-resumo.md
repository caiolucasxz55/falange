---
description: O que mudou, o que travou e o que esta em risco no Falange nos ultimos dias (so leitura)
argument-hint: [dias]
---

Conte como andou o trabalho no Falange nos ultimos `$ARGUMENTS` dias
(padrao: 7).

Use SOMENTE as tools do servidor MCP `falange`. **Isto e so leitura**: nao
crie, nao edite, nao conclua nada aqui.

## 1. Coletar

`resumo_periodo(dias=<N>)`. Ela ja junta o que voce precisa: throughput,
tempo de ciclo, contagem por tipo de evento, alertas da priorizacao e os
marcos com previsao.

Se vier `erro`, mostre e pare.

## 2. O aviso vem primeiro

Se a resposta tiver `aviso`, **diga isso antes de qualquer numero**. Ele
significa que ha pouco historico -- o registro de eventos comeca quando a
tabela passou a existir, e o que aconteceu antes nao aparece.

"Nao ha historico suficiente" e **diferente** de "o time nao fez nada", e
confundir os dois e a forma mais facil de este comando mentir.

## 3. Contar o que aconteceu

Em 3 a 6 linhas, nesta ordem:

1. **Entregue:** quantas tasks sairam no periodo, e por bloco se houver
   diferenca que valha citar.
2. **Ritmo:** o tempo de ciclo mediano, com o `n` que o sustenta. Mediana
   de 2 ciclos nao e ritmo, e coincidencia -- diga o `n` sempre.
3. **O que travou:** os `alertas`. Eles ja vem explicados (inversao,
   inflacao, trabalho parado, marco em risco); use o texto deles, nao
   invente razao.
4. **O que esta em risco:** cada marco de `em_risco`, com a conta que a
   previsao devolve ("12 dias de trabalho para 5 de calendario"). Numero,
   nao adjetivo.

## 4. Nao invente causa

Os numeros dizem O QUE aconteceu. Eles nao dizem POR QUE.

"O throughput caiu de 6 para 2" e um fato. "O time esta desmotivado" e um
palpite que voce nao tem como sustentar -- e que, dito por um software,
soa como se tivesse evidencia. Se quiser levantar hipotese, marque como
pergunta: "sairam 2 contra 6 da semana passada; houve feriado ou alguma
task grande travando?".

Variacao de uma semana para outra quase sempre e ruido. Comente tendencia
so quando houver 3 ou mais semanas na mesma direcao.

## 5. Fechar

Uma linha com o que merece atencao esta semana, e nada mais. Se houver um
marco atrasado, e ele.

Se aparecer algo que mereca virar trabalho, **ofereca** `/falange-nova` ou
`registrar_nota` -- nao crie nada por conta propria: este comando e de
leitura.
