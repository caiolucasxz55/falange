"""Normalizacao dos campos de texto livre que guardam NOME de pessoa.

Por que isto existe: `responsavel`, `autor` e `nome` sao digitados a mao, e
sem aparar os dois lados a mesma pessoa vira valores diferentes no banco.
O estrago nao e cosmetico:

- o filtro `?responsavel=Caio` nao acha a task gravada como `"Caio "`;
- `/carga` conta zero e a deteccao de sobrecarga fica silenciosamente errada;
- `responsavel_id` nao resolve, porque a busca por nome compara o texto
  aparado da entrada com o nome sujo gravado no usuario.

E sem tratar vazio como ausencia a coluna acumula tres representacoes do
mesmo fato -- `None`, `""` e `"   "` -- que nenhum filtro consegue cobrir de
uma vez. O MCP ja convertia `""` em None antes de enviar; a tela nao, e a
regra nao pode depender de qual cliente chamou.
"""

from typing import Annotated, Optional

from pydantic import BeforeValidator, StringConstraints

# Teto dos nomes de pessoa, igual ao da coluna no banco.
MAX_NOME = 80


def _sem_sobra(valor):
    """Apara, e trata o que sobrar vazio como ausencia.

    Nao-texto passa intacto para o pydantic reclamar do tipo com a mensagem
    dele, que e melhor que a que eu escreveria aqui.
    """
    if not isinstance(valor, str):
        return valor
    return valor.strip() or None


# Nome de pessoa opcional: aparado, e vazio virando None. Use em todo campo
# de nome livre que aceita ausencia (`responsavel`, `autor`).
#
# O `max_length` fica DENTRO do Optional, no `str`: aplicado por fora, ele
# tenta medir o None e estoura com "Unable to apply constraint". E ele mede o
# valor ja aparado, entao um nome de 80 chars com espaco em volta passa.
NomeOpcional = Annotated[
    Optional[Annotated[str, StringConstraints(max_length=MAX_NOME)]],
    BeforeValidator(_sem_sobra),
]

# Nome obrigatorio: so aparado. Vazio nao vira None aqui -- cai no
# min_length e a pessoa recebe um 422 dizendo que o nome e curto demais.
NomeObrigatorio = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=MAX_NOME),
]
