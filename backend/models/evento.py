"""Evento: o que aconteceu, quando e por quem.

As outras tabelas guardam o ESTADO ATUAL. Uma task diz que esta concluida;
nao diz quando saiu de aberta, quantas vezes voltou, nem quem a moveu. Essa
informacao existia e era jogada fora a cada escrita.

Daqui saem o `GET /evolucao` (throughput, tempo de ciclo) e o
`resumo_periodo` ("o que mudou esta semana"). Nenhum dos dois da para
calcular a partir do estado atual: eles sao sobre a passagem do tempo.

## Nao e auditoria, e nao tenta ser

Nao ha assinatura, nao ha cadeia de hash, e o registro mora na mesma
transacao do que ele descreve -- quem alcanca o banco altera os dois. Para
contar a evolucao do time isso basta. Para provar o que alguem fez contra a
vontade dessa pessoa, nao basta, e dizer que basta seria pior que nao ter.

## `dados` e proposital e deliberadamente frouxo

JSONB sem schema. O que interessa de "mudou o status" nao e o que interessa
de "ganhou dependencia", e inventar colunas para a uniao de todos os casos
daria uma tabela larga e quase toda nula. Quem le trata campo ausente como
desconhecido.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class TipoEvento(str, PyEnum):
    """O que aconteceu.

    Nomes no passado, porque evento e fato consumado. Um enum, e nao texto
    livre, para `GET /evolucao` poder contar sem adivinhar grafia.
    """

    task_criada = "task_criada"
    task_editada = "task_editada"
    task_mudou_status = "task_mudou_status"
    task_apagada = "task_apagada"

    dependencia_adicionada = "dependencia_adicionada"
    dependencia_removida = "dependencia_removida"

    evidencia_registrada = "evidencia_registrada"
    evidencia_apagada = "evidencia_apagada"

    nota_criada = "nota_criada"
    nota_resolvida = "nota_resolvida"
    nota_apagada = "nota_apagada"


class Evento(Base):
    __tablename__ = "evento"

    id: Mapped[int] = mapped_column(primary_key=True)
    projeto_id: Mapped[int] = mapped_column(
        ForeignKey("projeto.id", ondelete="CASCADE"), index=True
    )

    # Nulo quando o evento nao e de uma task (nota solta, por exemplo).
    #
    # SET NULL e nao CASCADE: apagar a task NAO pode apagar a historia
    # dela. "A task #12 foi apagada" e exatamente o evento que precisa
    # sobreviver a task #12 -- com CASCADE, ele se apagaria junto e o
    # registro mais importante seria o unico a sumir.
    task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task.id", ondelete="SET NULL"), nullable=True, index=True
    )

    tipo: Mapped[TipoEvento] = mapped_column(
        Enum(TipoEvento, name="tipo_evento"), index=True
    )

    # Quem fez. Nulo para evento anterior a identidade por pessoa, ou de
    # quem entrou sem login.
    autor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
    )

    dados: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Indexado porque TODA consulta daqui filtra por periodo: "a ultima
    # semana", "as 8 ultimas semanas". Sem indice, cada pergunta varre a
    # tabela inteira, que e a que mais cresce no banco.
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
