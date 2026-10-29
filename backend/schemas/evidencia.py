"""Contratos de entrada e saida da evidencia."""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.models.evidencia import (
    MAX_REFERENCIA,
    MAX_RESUMO,
    MAX_SHA,
    MIN_SHA,
    TipoEvidencia,
)

# Sha do git: hexadecimal, de 7 a 40 chars. Validar o FORMATO e o que da
# para fazer sem o repositorio na mao -- se o commit existe, quem confere e
# quem le, com `git show`. Recusar "sei la" como sha ja evita a prova
# decorativa mais obvia.
_SHA = re.compile(rf"^[0-9a-f]{{{MIN_SHA},{MAX_SHA}}}$")

# De 1 a 5, como os criterios: a lista nao pode ser maior que o que existe.
MAX_CRITERIOS_POR_EVIDENCIA = 5


class EvidenciaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    tipo: TipoEvidencia
    referencia: str
    resumo: str
    autor_id: Optional[int] = None
    criada_em: datetime


class EvidenciaNova(BaseModel):
    """Uma prova, e quais criterios ela cumpre."""

    tipo: TipoEvidencia
    referencia: str = Field(default="", max_length=MAX_REFERENCIA)
    resumo: str = Field(default="", max_length=MAX_RESUMO)
    # Quais criterios esta prova cumpre. Vazia e aceito: a evidencia fica
    # anexada a task sem fechar criterio nenhum, o que e o caso de uma nota
    # de contexto.
    criterio_ids: list[int] = Field(
        default_factory=list, max_length=MAX_CRITERIOS_POR_EVIDENCIA
    )

    @model_validator(mode="after")
    def _prova_tem_de_apontar_para_algo(self):
        """O que cada tipo exige para nao ser uma prova vazia.

        `commit` e `teste` sao conferiveis por terceiros, entao a referencia
        e obrigatoria -- uma evidencia de commit sem sha nao prova nada e
        ainda assim destravaria a conclusao, que e pior que nao ter prova.

        `manual` nao tem referencia para dar, e por isso exige o resumo: a
        unica coisa que alguem vai poder ler depois e o texto.
        """
        referencia = (self.referencia or "").strip()
        resumo = (self.resumo or "").strip()

        if self.tipo == TipoEvidencia.commit:
            if not _SHA.match(referencia.lower()):
                raise ValueError(
                    f"referencia '{referencia}' nao parece um sha de commit: "
                    f"use de {MIN_SHA} a {MAX_SHA} chars hexadecimais"
                )
            self.referencia = referencia.lower()
        elif self.tipo == TipoEvidencia.teste:
            if not referencia:
                raise ValueError(
                    "evidencia de teste precisa da referencia: o teste que "
                    "cobre o criterio (ex.: tests/test_grafo.py::test_ciclo)"
                )
            self.referencia = referencia
        elif self.tipo == TipoEvidencia.link:
            if not referencia:
                raise ValueError("evidencia de link precisa da URL na referencia")
            self.referencia = referencia
        else:
            # manual
            if not resumo:
                raise ValueError(
                    "evidencia manual precisa do resumo: sem referencia para "
                    "conferir, o texto e a unica prova que sobra"
                )
            self.referencia = referencia

        self.resumo = resumo
        if len(set(self.criterio_ids)) != len(self.criterio_ids):
            raise ValueError("criterio_ids tem id repetido")
        return self
