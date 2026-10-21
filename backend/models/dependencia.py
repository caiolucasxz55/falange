"""Dependencia entre tasks: uma task pode esperar por VARIAS.

Substitui a coluna `task.bloqueada_por`, que so cabia uma. Com uma tabela,
a relacao vira um grafo -- e as contas sobre ele (ciclo, cadeia, quem
destrava quem) moram em `dominio/grafo.py`, puras.

"Bloqueada" deixa de existir como coluna: e DERIVADA de ter dependencia nao
concluida. Guardar o estado obrigava a limpar o bloqueio de quem esperava
toda vez que uma task era concluida, e esquecer isso em algum caminho
deixava task travada por algo que ja tinha acabado.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Dependencia(Base):
    """`task_id` nao anda enquanto `depende_de_id` nao terminar.

    PK composta: a mesma dupla nao entra duas vezes, e o banco garante isso
    sem precisar de checagem na aplicacao.

    CASCADE nos dois lados: apagar qualquer uma das pontas apaga a aresta.
    Sem isso sobraria aresta apontando para id morto, e o grafo mentiria.
    """

    __tablename__ = "dependencia"

    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"), primary_key=True
    )
    depende_de_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
