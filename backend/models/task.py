"""A task: a unidade de trabalho do time.

Deliberadamente pequena: sem epico, sem sprint. Essa e a simplificacao em
relacao ao Jira, nao uma etapa faltando.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base
from backend.models.enums import Bloco, Estimativa, Origem, Prioridade, Status


class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(Text, default="")
    estimativa: Mapped[Estimativa] = mapped_column(Enum(Estimativa, name="estimativa"))
    bloco: Mapped[Bloco] = mapped_column(Enum(Bloco, name="bloco"))

    # O texto continua, e nao e legado: e o rotulo de quem nunca virou
    # conta no Falange (alguem de outro time, um nome escrito a mao). Quando
    # a pessoa existe como usuario, `responsavel_id` aponta para ela e passa
    # a ser a verdade; o texto fica como o que a tela mostra.
    responsavel: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    responsavel_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Quem criou a task. Nulo nas tasks de antes da V2, quando nao havia
    # usuario para apontar. `origem` diz se foi IA ou humano; isto diz quem.
    autor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Auto-referencia: esta task esta travada POR outra task.
    bloqueada_por: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[Status] = mapped_column(
        Enum(Status, name="status"), default=Status.aberta
    )

    prioridade: Mapped[Prioridade] = mapped_column(
        Enum(Prioridade, name="prioridade"), default=Prioridade.media, index=True
    )

    # Default humano: so o MCP marca ia, entao task antiga nao vira da IA.
    origem: Mapped[Origem] = mapped_column(
        Enum(Origem, name="origem"), default=Origem.humano
    )

    # Marcos de tempo. O repositorio atualiza atualizada_em explicitamente em
    # cada escrita: sem trigger no banco, para a regra ficar visivel no codigo.
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Primeira ida para em_andamento; nao e sobrescrita depois.
    iniciada_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Volta a NULL se a task for reaberta.
    concluida_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
