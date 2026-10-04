---
description: Sugere caminhos para a proxima task do Falange, pergunta qual seguir e executa so o escolhido
argument-hint: [responsavel]
---

Ajude o dev a decidir o que fazer agora no Falange. Responsavel: `$ARGUMENTS`
(opcional).

Use SOMENTE as tools do servidor MCP `falange`. Voce SUGERE; quem decide e o
dev.

## 1. Coletar

1. `ver_configuracao` - guarde `perguntas_ativas`.
2. `sugerir_proximas` com `responsavel` (se veio) e `limite: 5`.

Se vier `erro`, mostre e pare. Se `sugestoes` estiver vazia, diga que nao ha
task livre (provavelmente tudo bloqueado ou concluido) e mostre os `alertas`.

## 2. Montar de 2 a 3 CAMINHOS

Caminho nao e item de lista: e uma escolha com consequencia. Cada um tem
**o que fazer**, **por que** (use os `motivos`, nao invente razao) e **o
custo**. Tire os caminhos do que os dados mostram, por exemplo:

- "pegar #7, a mais prioritaria" - custo: #3 segue travando outras;
- "destravar #3 antes, porque libera 2 tasks" - custo: adia a mais prioritaria;
- "terminar #5, parada ha 6 dias" - custo: nada novo comeca hoje.

Regras:

- Se houver alerta de `inversao`, um dos caminhos e corrigir a prioridade da
  task que trava a alta.
- Se houver `avisos` de sobrecarga, diga isso antes dos caminhos: pode ser
  que o certo seja nao pegar nada novo.
- Nao repita o ranking inteiro. Dois ou tres caminhos bem diferentes valem
  mais que cinco variacoes do mesmo.

## 3. Escolher

**Se `perguntas_ativas` for true:** pergunte qual caminho, com AskUserQuestion
se a ferramenta estiver disponivel; senao, lista numerada. Uma opcao por
caminho, mais "nenhum, so queria ver". **Termine a sua vez e espere.**

**Se for false:** nao pergunte. Siga o primeiro caminho, diga em uma linha
que seguiu sozinho porque as perguntas estao desligadas, e qual foi o
criterio.

## 4. Executar so o escolhido

- "pegar/terminar a task X" -> `mudar_status` para `em_andamento`.
- "corrigir a prioridade" -> `editar_task` com a nova prioridade.
- "destravar" -> depende do caso: pode ser pegar a bloqueadora
  (`mudar_status`) ou remover um bloqueio que nao faz mais sentido
  (`marcar_bloqueio` com `bloqueada_por: null`). Confirme qual antes de
  mexer, se nao estiver obvio.

Nao execute os caminhos descartados. Nao crie task nova aqui.

## 5. Fechar

Uma linha com o que mudou (`#id` e o novo estado) e os alertas que seguem
abertos. Lembre que a tela mostra isso em http://localhost:3010.
