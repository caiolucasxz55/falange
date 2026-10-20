"""Contratos de projeto."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from backend.models.projeto import MAX_NOME_PROJETO, MAX_SLUG, PADRAO_SLUG

# O slug viaja no header `X-Falange-Projeto` e na env do MCP, entao precisa
# ser previsivel: minusculas, digitos e hifen, sem hifen nas pontas.
Slug = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=2,
        max_length=MAX_SLUG,
        pattern=PADRAO_SLUG,
    ),
]


class ProjetoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    nome: str
    criado_em: datetime


class ProjetoNovo(BaseModel):
    slug: Slug
    nome: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=2, max_length=MAX_NOME_PROJETO
        ),
    ]


class ProjetoAtual(BaseModel):
    """Em que projeto a chamada caiu.

    A IA usa para confirmar o contexto antes de escrever, e a tela para
    desenhar o seletor. `padrao` diz se e o projeto que recebe quem nao
    manda o header.
    """

    projeto: ProjetoOut
    padrao: bool
