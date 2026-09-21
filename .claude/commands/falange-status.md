---
description: Panorama das tasks do Falange - blocos, bloqueios e sobrecarga (so leitura)
argument-hint: [bloco ou responsavel, opcional]
---

Mostre o panorama atual das tasks do Falange. Filtro opcional: `$ARGUMENTS`
(um bloco - frontend, backend, infra, seguranca - ou o nome de um responsavel).

Use SOMENTE tools de leitura do servidor MCP `falange`: `listar_tasks`,
`contar_tasks_por_bloco` e `verificar_sobrecarga`. Nao crie, edite nem apague nada.

## Coletar

1. `contar_tasks_por_bloco`.
2. `listar_tasks` (aplique o filtro, se houver).
3. `verificar_sobrecarga` para cada bloco que tem tasks e para cada
   `responsavel` distinto que aparece na lista.

## Mostrar

Seja curto. Nesta ordem:

1. **Totais**: tasks por bloco e por status (aberta / em_andamento / concluida).
2. **Bloqueios**: cada task com `bloqueada_por`, mostrando a cadeia inteira
   quando houver mais de um nivel (A trava B, B trava C: diga que o problema
   de C esta em A).
3. **Sobrecarga**: so o que tiver `sobrecarregado: true`, com
   `tasks_abertas` / `limite`. Se nada estiver, diga isso em uma linha.
4. **Abertas**: tabela `#id | titulo | estimativa | bloco | status | responsavel`,
   sem as concluidas.

Termine com no maximo duas observacoes, e so se forem uteis: por exemplo, um
bloco sem nenhuma task, ou uma task G que talvez devesse ser quebrada.
