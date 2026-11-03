"""Marco: uma entrega com data, agrupando tasks.

Existe para dar DADO REAL a uma regra que ja estava escrita. A regra de
prioridade sempre disse que `alta` vale quando a task "e pre-requisito de
uma entrega proxima" -- mas nada no sistema sabia o que era uma entrega,
nem quando ela era. Quem decidia era a memoria de quem estava olhando.

Deliberadamente raso: sem sprint, sem epico, sem hierarquia. Um marco e um
nome e uma data; a task aponta para ele ou nao aponta. A simplificacao em
relacao ao Jira e o ponto, nao uma etapa faltando.
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

MAX_NOME = 120


class Marco(Base):
    __tablename__ = "marco"

    id: Mapped[int] = mapped_column(primary_key=True)
    projeto_id: Mapped[int] = mapped_column(
        ForeignKey("projeto.id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(MAX_NOME))

    # `Date`, nao `DateTime`: um prazo de entrega e um dia, nao um
    # instante. Guardar hora traria fuso para uma conta que e de
    # calendario, e "vence as 23:59 de onde?" e uma pergunta sem resposta
    # boa num time distribuido.
    #
    # Nulo = marco sem prazo. A previsao devolve `sem_data` nesse caso, em
    # vez de fingir um veredito.
    data_alvo: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Preenchido ao fechar. A linha NAO e apagada, como na sessao e no
    # token: um marco entregue e justamente o que se quer poder olhar
    # depois.
    fechado_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
