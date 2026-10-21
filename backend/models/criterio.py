"""Criterio de aceite: como se sabe que a task acabou.

Antes isso era uma LINHA na descricao ("Criterio de aceite: ..."), exigida
pelo lint da pre-task. Servia para a pessoa ler, e so: nada no sistema sabia
quantos criterios a task tinha, nem quais faltavam. Em tabela, cada um e um
item que pode ser cumprido por conta propria.

`cumprido_em` e `evidencia_id` existem para a Fase F, onde concluir uma task
passa a pedir evidencia por criterio. Aqui eles so nascem vazios: nada no
caminho da E2 os preenche, e a tela mostra a lista como checklist de leitura.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

# De 1 a 5 por task. O teto nao e arbitrario: uma task que precisa de seis
# criterios para ser explicada e duas tasks.
MIN_CRITERIOS = 1
MAX_CRITERIOS = 5

# Curto demais nao e observavel ("ok", "funciona"); longo demais e descricao
# disfarcada de criterio.
MIN_TEXTO_CRITERIO = 10
MAX_TEXTO_CRITERIO = 200


class Criterio(Base):
    __tablename__ = "criterio"
    # A ordem e do usuario, nao do id: a lista e lida de cima para baixo, e
    # dois criterios na mesma posicao nao teriam como ser desenhados.
    __table_args__ = (
        UniqueConstraint("task_id", "ordem", name="uq_criterio_task_ordem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Sem `projeto_id`: o criterio pertence a task, e a task ao projeto.
    # Guardar de novo aqui abriria a chance de os dois discordarem.
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"), index=True
    )
    texto: Mapped[str] = mapped_column(Text)
    ordem: Mapped[int] = mapped_column()

    # Preenchidos na Fase F. Nulo = ainda nao verificado.
    cumprido_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
