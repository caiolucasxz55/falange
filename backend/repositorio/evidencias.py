"""Consultas e escritas da evidencia.

Como no resto do pacote: nao levanta `HTTPException`. Devolve `None`,
`False` ou uma tupla `(valor, erro)` e deixa a rota traduzir para HTTP.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Criterio, Evidencia, TipoEvidencia


async def listar_por_task(
    session: AsyncSession, task_id: int
) -> list[Evidencia]:
    q = (
        select(Evidencia)
        .where(Evidencia.task_id == task_id)
        .order_by(Evidencia.criada_em, Evidencia.id)
    )
    return list((await session.scalars(q)).all())


async def por_task(
    session: AsyncSession, task_ids: list[int]
) -> dict[int, list[Evidencia]]:
    """As evidencias das tasks pedidas, agrupadas. Uma consulta, nao N."""
    if not task_ids:
        return {}
    q = (
        select(Evidencia)
        .where(Evidencia.task_id.in_(task_ids))
        .order_by(Evidencia.task_id, Evidencia.criada_em, Evidencia.id)
    )
    agrupadas: dict[int, list[Evidencia]] = {}
    for evidencia in (await session.scalars(q)).all():
        agrupadas.setdefault(evidencia.task_id, []).append(evidencia)
    return agrupadas


async def registrar(
    session: AsyncSession,
    task_id: int,
    tipo: TipoEvidencia,
    referencia: str,
    resumo: str,
    autor_id: Optional[int],
    criterio_ids: list[int],
) -> tuple[Optional[Evidencia], Optional[str]]:
    """Grava a prova e liga os criterios pedidos, no mesmo commit.

    `(evidencia, None)` no sucesso, `(None, erro)` quando algum
    `criterio_id` nao e daquela task. Nao e detalhe: aceitar id de outra
    task deixaria uma evidencia "cumprindo" criterio alheio e destravaria a
    conclusao de uma task que ninguem provou.
    """
    pedidos = set(criterio_ids)
    if pedidos:
        q = select(Criterio.id).where(
            Criterio.id.in_(pedidos), Criterio.task_id == task_id
        )
        da_task = set((await session.scalars(q)).all())
        forasteiros = sorted(pedidos - da_task)
        if forasteiros:
            quais = ", ".join(str(i) for i in forasteiros)
            return None, (
                f"criterio {quais} nao e da task {task_id}"
            )

    evidencia = Evidencia(
        task_id=task_id,
        tipo=tipo,
        referencia=referencia,
        resumo=resumo,
        autor_id=autor_id,
    )
    session.add(evidencia)
    # Flush para ter o id da evidencia antes de apontar os criterios para
    # ela, ainda dentro da mesma transacao.
    await session.flush()

    if pedidos:
        await session.execute(
            update(Criterio)
            .where(Criterio.id.in_(pedidos))
            .values(
                evidencia_id=evidencia.id,
                cumprido_em=datetime.now(timezone.utc),
            )
        )

    await session.commit()
    await session.refresh(evidencia)
    return evidencia, None


async def remover(
    session: AsyncSession, task_id: int, evidencia_id: int
) -> bool:
    """False quando a evidencia nao existe ou nao e daquela task.

    O criterio volta a "nao verificado": a FK e SET NULL, mas `cumprido_em`
    e coluna propria e tem de ser limpa aqui -- deixar a data sem a prova
    diria que o criterio foi cumprido sem nada para mostrar.
    """
    alvo: Optional[Evidencia] = await session.get(Evidencia, evidencia_id)
    if alvo is None or alvo.task_id != task_id:
        return False

    await session.execute(
        update(Criterio)
        .where(Criterio.evidencia_id == evidencia_id)
        .values(evidencia_id=None, cumprido_em=None)
    )
    await session.delete(alvo)
    await session.commit()
    return True
