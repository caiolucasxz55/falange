"""Nota: o registro do time que nao e task."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Nota(Base):
    """Registro solto do time: problema, decisao ou duvida que precisa de mais
    gente. Existe para nao virar task bloqueada so para ser discutida."""

    __tablename__ = "nota"

    id: Mapped[int] = mapped_column(primary_key=True)
    texto: Mapped[str] = mapped_column(Text)

    # Mesma ideia do responsavel da task: o texto e o rotulo, o id e o fato.
    autor: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    autor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Nota pode nascer solta; se a task some, a nota sobrevive sem ela.
    task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task.id", ondelete="SET NULL"), nullable=True
    )

    resolvida: Mapped[bool] = mapped_column(Boolean, default=False)
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
