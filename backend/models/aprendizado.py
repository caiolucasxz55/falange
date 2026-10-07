"""A memoria do Falange: decisao, preferencia e autonomia.

Tres tabelas, um assunto. O modelo nao aprende entre sessoes; estas tabelas
aprendem, e e por isso que elas ficam juntas.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base
from backend.models.enums import (
    NivelAutonomia,
    OrigemPreferencia,
    TipoAcao,
    TipoDecisao,
)


class Decisao(Base):
    """Uma escolha feita com opcoes: o que foi sugerido e o que foi escolhido."""

    __tablename__ = "decisao"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoDecisao] = mapped_column(
        Enum(TipoDecisao, name="tipo_decisao"), index=True
    )
    sugerido: Mapped[dict] = mapped_column(JSONB)
    escolhido: Mapped[dict] = mapped_column(JSONB)
    aceita: Mapped[bool] = mapped_column(Boolean)
    motivo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsavel: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    # Quem registrou. Importa para o perfil: saber de QUEM e o habito e o
    # que separa "o time escolhe P" de "uma pessoa escolhe P".
    autor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )
    task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task.id", ondelete="SET NULL"), nullable=True
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Preferencia(Base):
    """Regra que o time quer que a IA siga.

    Explicita nasce ativa (alguem pediu). Inferida nasce inativa: padrao
    detectado nos dados so vale depois de um humano confirmar.
    """

    __tablename__ = "preferencia"

    id: Mapped[int] = mapped_column(primary_key=True)
    descricao: Mapped[str] = mapped_column(String(200))
    origem: Mapped[OrigemPreferencia] = mapped_column(
        Enum(OrigemPreferencia, name="origem_preferencia")
    )
    ativa: Mapped[bool] = mapped_column(Boolean, default=False)
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Autonomia(Base):
    """Quanto a IA pode fazer sozinha, por tipo de acao.

    Sobe so com sim explicito do humano; desce sozinho na primeira
    discordancia (ver backend/dominio/autonomia.py).
    """

    __tablename__ = "autonomia"

    tipo_acao: Mapped[TipoAcao] = mapped_column(
        Enum(TipoAcao, name="tipo_acao"), primary_key=True
    )
    nivel: Mapped[NivelAutonomia] = mapped_column(
        Enum(NivelAutonomia, name="nivel_autonomia"),
        default=NivelAutonomia.perguntar,
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
