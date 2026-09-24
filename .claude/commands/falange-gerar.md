---
description: Transforma um arquivo de documentacao ou codigo em tasks do Falange (sugere, valida, cria apos sua aprovacao)
argument-hint: <caminho do arquivo>
---

Gere tasks do Falange a partir do arquivo `$ARGUMENTS`.

Use SOMENTE as tools do servidor MCP `falange`. Nao leia o arquivo com Read,
nao edite codigo, nao acesse o banco. Se `$ARGUMENTS` estiver vazio, pergunte
o caminho e pare.

## 1. Ler

Chame `gerar_tasks_a_partir_de_arquivo` com `caminho: "$ARGUMENTS"`.

- Se voltar `erro`, mostre a mensagem e pare. "Fora da raiz permitida"
  significa que o arquivo esta fora de `FALANGE_DOCS_ROOT`.
- `template` e a regra de escrita: siga exatamente.
- `tasks_existentes` e o que ja existe: nao proponha duplicata.
- `estrutura` (titulos, TODO/FIXME, itens de lista) e o mapa do que o
  arquivo pede.

## 2. Redigir

Escreva as pre-tasks seguindo o `template`.

- Uma task = uma entrega verificavel. Nao agrupe assuntos diferentes.
- So proponha o que o arquivo sustenta. Nao invente escopo.
- Poucas tasks boas valem mais que muitas vagas.
- Se uma task so pode comecar depois de outra, anote a dependencia pelo
  numero da lista (ex.: "3 depende de 1").

## 3. Validar

Chame `validar_task` para cada pre-task (`titulo`, `descricao`, `estimativa`,
`bloco`).

- `precisa_de_ajuste`: reescreva resolvendo cada item de `motivos` e valide
  de novo. No maximo 2 correcoes por task. Se ainda reprovar, mantenha como
  reprovada e mostre os motivos.
- Corrija o conteudo, nao o lint: nada de colar "Criterio de aceite:" sem
  um criterio de verdade, nem inflar texto para passar do minimo.
- Se a estimativa for questionada, use `estimativa_sugerida` como referencia,
  mas prefira quebrar uma task G em duas quando fizer sentido.

## 4. Revisao (obrigatoria)

Mostre uma tabela: numero, titulo, bloco, estimativa, prioridade, veredito,
depende de. Abaixo dela, a descricao de cada uma.

Pergunte quais criar: todas as aprovadas, uma lista de numeros, ou nenhuma.
Pergunte tambem se ha um `responsavel`.

**Nao chame `criar_task` antes da resposta.** Termine a sua vez aqui.

## 5. Criar

Para as escolhidas:

1. `criar_task` para cada uma. Guarde o `id` real devolvido.
2. `marcar_bloqueio` para cada dependencia anotada, com os ids reais
   (`task_id` = a que espera, `bloqueada_por` = a que precisa sair antes).
   Se voltar `erro` (ex.: ciclo), reporte e siga.

## 6. Relatorio

Liste o que foi criado (`#id titulo [estimativa/bloco/prioridade]`), com as
de prioridade alta primeiro, e os bloqueios.
Chame `contar_tasks_por_bloco` e mostre o total por bloco.

Diga que as tasks aparecem em http://localhost:3010 ao clicar em
**Recarregar**.
