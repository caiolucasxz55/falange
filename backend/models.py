"""Modelo de dados do Falange V1.

Deliberadamente pequeno: UMA tabela. Sem epico, sem sprint, sem board.
Essa e a simplificacao em relacao ao Jira, nao uma etapa faltando.
"""

from enum import Enum as PyEnum
from typing import Optional

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Estimativa(str, PyEnum):
    PP = "PP"
    P = "P"
    M = "M"
    G = "G"


class Bloco(str, PyEnum):
    frontend = "frontend"
    backend = "backend"
    infra = "infra"
    seguranca = "seguranca"


class Prioridade(str, PyEnum):
    alta = "alta"
    media = "media"
    baixa = "baixa"


class Status(str, PyEnum):
    # Nao existe "bloqueada" aqui de proposito: bloqueio e representado por
    # bloqueada_por. Duas fontes de verdade para o mesmo fato divergem sempre.
    aberta = "aberta"
    em_andamento = "em_andamento"
    concluida = "concluida"


ABERTAS = (Status.aberta, Status.em_andamento)


class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(Text, default="")
    estimativa: Mapped[Estimativa] = mapped_column(Enum(Estimativa, name="estimativa"))
    bloco: Mapped[Bloco] = mapped_column(Enum(Bloco, name="bloco"))

    # Texto simples, nao FK para usuario. Multi-usuario/auth e V2.
    responsavel: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

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

    # Marcos de tempo. O crud atualiza atualizada_em explicitamente em cada
    # escrita: sem trigger no banco, para a regra ficar visivel no codigo.
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
