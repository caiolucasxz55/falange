"""Comportamento da plataforma, editavel em runtime."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Configuracao(Base):
    """Chave/valor de comportamento da plataforma, editavel em runtime.

    Hoje guarda so `perguntas_ativas`: com ela desligada, a IA decide sozinha
    em vez de abrir opcoes. Tabela generica para nao precisar de migration a
    cada chave nova.
    """

    __tablename__ = "configuracao"

    chave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(String(200))
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
