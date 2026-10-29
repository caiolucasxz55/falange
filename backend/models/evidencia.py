"""Evidencia: a prova de que um criterio de aceite foi cumprido.

Existe por causa de uma assimetria. Quando um dev diz "terminei", ele
responde por isso -- tem nome, cara e historico no time. Quando a IA diz
"terminei", nao responde por nada: na sessao seguinte ela nao lembra de ter
dito. Entao a afirmacao dela nao vale como fato, e o que vale e o que da
para conferir depois dela ter ido embora.

Uma evidencia pode cobrir varios criterios (um commit que cumpre tres), por
isso a ligacao mora em `criterio.evidencia_id` e nao aqui.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

# Sha curto do git tem 7; o completo, 40.
MIN_SHA = 7
MAX_SHA = 40
MAX_REFERENCIA = 500
MAX_RESUMO = 500


class TipoEvidencia(str, PyEnum):
    """De onde a prova vem, da mais forte para a mais fraca.

    `commit` e `teste` sao conferiveis por qualquer um, depois, sem
    depender de quem registrou. `link` e `manual` dependem de confiar em
    quem escreveu -- continuam valendo, mas quem le sabe o que esta lendo.
    """

    commit = "commit"
    teste = "teste"
    link = "link"
    manual = "manual"


class Evidencia(Base):
    __tablename__ = "evidencia"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Sem `projeto_id`: a evidencia pertence a task, e a task ao projeto.
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[TipoEvidencia] = mapped_column(
        Enum(TipoEvidencia, name="tipo_evidencia")
    )
    # O sha, o nome do teste, a URL, ou vazio no tipo manual.
    referencia: Mapped[str] = mapped_column(String(MAX_REFERENCIA), default="")
    # O que essa prova mostra, em uma frase.
    resumo: Mapped[str] = mapped_column(Text, default="")

    # Quem registrou. Nao e derivavel de `origem` como na task: aqui
    # importa a conta, porque evidencia registrada pela IA e exatamente o
    # que um humano vai querer auditar.
    autor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
