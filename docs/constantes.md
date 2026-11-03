# Revisao das constantes, com os dados do proprio Falange

Fase I da V2. **Isto e um relatorio, nao uma mudanca.** Nenhuma constante
foi alterada: quem decide o que muda e voce.

Lido em 03/11/2026, do projeto `padrao` (o backlog real). O projeto
`falange` ainda nao existe, entao a amostra e a do backlog que esta em uso
-- pequena, e isso esta dito em cada secao.

---------------------------------------------------------------------------

## 1. A calibracao esta inerte, e isso trava a fase G

**O numero:** `n = 0` em todas as classes. `n_total = 0`.

```
PP  n=0   P  n=0   M  n=0   G  n=0
```

**Por que:** `dominio/calibracao.py` mede dias entre `iniciada_em` e
`concluida_em`, e **descarta a task que nao tem os dois**. As tasks
concluidas do backlog real foram fechadas sem nunca passar por
`em_andamento`:

| Task | iniciada_em | concluida_em |
|---|---|---|
| #72 Exigir login por pessoa | `null` | 17/10 |
| #73 Guardar a sessao em cookie | `null` | 17/10 |

**Por que importa mais do que parece:** a previsao de marco (fase G) usa a
calibracao para saber quanto vale cada classe. Com `n=0`, ela cai na faixa
nominal **sempre**. O ciclo "o Falange aprende com o time" existe no codigo
e nunca roda.

**O que eu NAO proponho:** medir `criada_em -> concluida_em` quando falta o
inicio. Isso mediria tempo de fila, nao de trabalho, e misturaria as duas
coisas numa mediana so -- o numero ficaria grande e sem significado, e
pior: pareceria calibrado.

**Tres caminhos, e o custo de cada um:**

1. **Nao mexer em constante; mudar o habito.** Passar por `em_andamento`
   antes de concluir. O `/falange-trabalhar` ja faz isso.
   Custo: so funciona para o que vier depois; o passado continua perdido.
2. **Concluir sem passar por em_andamento passa a marcar `iniciada_em`**
   com o instante da conclusao. Custo: duracao zero entra na mediana e
   puxa tudo para baixo -- calibracao errada e pior que calibracao
   ausente, porque a ausente avisa.
3. **Medir pelos EVENTOS** (fase G2), que registram cada transicao, e
   deixar `iniciada_em` para tras. Custo: so vale para o que foi
   registrado depois da tabela existir, e e mais codigo.

Minha recomendacao e **(1)**, sem tocar em constante nenhuma. O problema
nao e o limiar, e o fluxo de uso.

---------------------------------------------------------------------------

## 2. `idade_teto` saturou: a idade parou de diferenciar

**Os numeros**, do `sugerir_proximas` de hoje:

| Task | Prioridade | Dias aberta | Score |
|---|---|---|---|
| #70 | alta | 16 | 55 |
| #1 | media | 40 | 40 |
| #5 | media | 40 | 40 |
| #7 | media | 40 | 40 |

`PESOS["idade_teto"] = 15`, e `idade_por_dia = 1`. Toda task com **15 dias
ou mais** recebe exatamente 15. As tres de 40 dias empataram, e o
desempate caiu no id -- ou seja, na ordem de criacao, que nao e um
criterio.

**Quanto tempo o teto cobre:** 15 dias. O backlog tem task de 40.

**Proposta:** subir `idade_teto` para **30**. Mantem o papel original (a
idade nao pode dominar o ranking) e volta a diferenciar na faixa em que as
tasks deste projeto de fato vivem.

**Contra-argumento honesto:** com 30, uma task media esquecida ha 30 dias
chega a 45 e passa uma task alta recem-criada (30). Isso pode ser certo --
"ninguem olha isso ha um mes" e informacao -- ou pode ser o ranking
passando por cima da intencao do time. **E a sua decisao**, nao minha: o
peso da idade contra a prioridade declarada e uma questao de como o time
quer trabalhar, nao de ajuste tecnico.

---------------------------------------------------------------------------

## 3. `prioridade_media` + `idade_teto` ja empata com `alta`

**Os numeros:** `prioridade_alta = 30`, `prioridade_media = 15`,
`idade_teto = 15`.

Uma task **media** parada ha 15 dias vale `15 + 15 = 30`. Uma task **alta**
criada hoje vale `30`. Empate.

Isso ja acontece hoje, sem mudar nada. Nao e necessariamente errado -- o
alerta de inflacao existe justamente porque "alta" e barato de declarar --
mas vale saber que a escada atual ja permite a idade anular a prioridade.

**Nao proponho mudanca.** So registro, porque ninguem tinha calculado.

---------------------------------------------------------------------------

## 4. `DIAS_PARADA = 5`: dois alertas, os dois legitimos

```
#70 em andamento ha 16 dias
#69 em andamento ha 16 dias
```

Duas das tres tasks em andamento estao paradas ha mais de tres vezes o
limiar. O limiar esta fazendo o trabalho dele: pegou o que devia pegar, e
nao gerou alerta de nada que esteja andando.

**Nao proponho mudanca.** Amostra pequena, mas sem sinal de erro.

---------------------------------------------------------------------------

## 5. `JANELA = 5` e os limiares do perfil: sem dados para julgar

| Constante | Valor | O que os dados dizem |
|---|---|---|
| `JANELA` (autonomia) | 5 | nenhuma acao chegou perto; `aceitas_seguidas = 0` |
| `minimo_ocorrencias` (perfil) | 5 | 1 padrao candidato achado, com 11 ocorrencias |
| `consistencia_minima` | 0.8 | o candidato saiu com 0.85 -- passou raspando |
| `AMOSTRA_MINIMA` (calibracao) | 5 | nunca foi testado: ver secao 1 |

O unico padrao candidato detectado ("em estimativa, o time escolhe P",
11/13, consistencia 0.85) passou do limiar por 0.05. Com `0.9`, ele nao
teria aparecido. Um unico caso nao diz se 0.8 e generoso demais -- mas
diz que o limiar esta na faixa em que as coisas ficam perto, que e onde ele
deve estar.

**Nao proponho mudanca.** Rever quando houver 3 ou 4 candidatos.

---------------------------------------------------------------------------

## Resumo

| # | Constante | Proposta |
|---|---|---|
| 1 | nenhuma | o problema e o fluxo de uso, nao o limiar |
| 2 | `idade_teto` 15 -> 30 | **sua decisao**: muda a relacao idade x prioridade |
| 3 | nenhuma | so registro |
| 4 | `DIAS_PARADA` | manter |
| 5 | `JANELA`, limiares do perfil | manter, rever com mais dados |

Uma so proposta de mudanca, e ela depende de uma escolha que nao e tecnica.
As constantes estao, no geral, no lugar certo -- o que esta faltando nao e
ajuste, e **uso**: quase toda a amostra deste relatorio e pequena porque o
Falange ainda nao foi usado para construir o Falange.

E para isso que serve a virada: criar o projeto `falange` e passar a
trabalhar por ele.
