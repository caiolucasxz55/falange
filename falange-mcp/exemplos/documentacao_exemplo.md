# Falange - Notas tecnicas do modulo de Sprint

## Contexto

Hoje o time abre tarefa no board sem criterio de aceite e sem estimativa.
O resultado e que ninguem sabe o que esta travado nem quem esta afogado.
Este documento descreve o que precisa existir para o modulo de sprint sair
do papel.

## Importacao de backlog

Precisamos aceitar um CSV exportado do Jira e transformar em tasks do
Falange. O mapeamento de campos nao e obvio: "Story Points" vira nossa
faixa PP/P/M/G, e "Epic Link" e descartado (nao temos epico por decisao
de produto). Linhas invalidas nao podem derrubar a importacao inteira -
precisam ir para um relatorio de erro no final.

TODO: decidir o que fazer quando o CSV tem task duplicada por titulo.

## Visualizacao de dependencia

Quando uma task esta bloqueada por outra, o time precisa ver a cadeia
inteira, nao so o vizinho imediato. Se A trava B e B trava C, quem olha C
precisa saber que o problema real esta em A. Hoje nao temos nada disso.

Cuidado: e possivel criar ciclo (A trava B, B trava A). O backend precisa
recusar isso na hora da escrita.

## Alerta de sobrecarga

- contar tasks abertas por pessoa
- comparar com um limite configuravel por time
- destacar quem passou do limite
- nao enviar e-mail ainda, so expor no endpoint

## Migracao para Postgres

O prototipo guarda tudo em memoria e perde os dados no restart. Precisamos
migrar para Postgres com migration versionada, porque o schema vai mudar
quando entrar multi-usuario no V2.

## Cache de contagem

As telas de contagem por bloco batem no banco a cada carregamento. Quando
passar de alguns milhares de tasks isso vai pesar. Avaliar cache, mas
nao antes de medir - pode ser cedo demais.

FIXME: o endpoint de contagem nao filtra por status, entao task concluida
ainda conta como carga da pessoa.
