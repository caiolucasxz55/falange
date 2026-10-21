"""Consultas e escritas dos criterios de aceite.

Criterio nao tem rota propria: ele nasce com a task e e lido junto dela.
Por isso aqui so ha o que a task precisa -- criar a lista e buscar por
varias tasks de uma vez.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Criterio


async def criar_para(
    session: AsyncSession, task_id: int, textos: list[str]
) -> None:
    """Grava a lista na ordem recebida. Nao commita: quem criou a task commita.

    A ordem e a da lista, nao a do id: e nela que a pessoa escreveu o
    checklist, e reordenar por id daria o mesmo resultado so por acidente.
    """
    for ordem, texto in enumerate(textos):
        session.add(Criterio(task_id=task_id, texto=texto, ordem=ordem))


async def por_task(
    session: AsyncSession, task_ids: list[int]
) -> dict[int, list[Criterio]]:
    """Os criterios das tasks pedidas, agrupados por task_id.

    Uma consulta para a lista inteira, nao uma por task: o board carrega
    dezenas de cards de uma vez, e `montar_tasks` seria N+1.
    """
    if not task_ids:
        return {}

    q = (
        select(Criterio)
        .where(Criterio.task_id.in_(task_ids))
        .order_by(Criterio.task_id, Criterio.ordem)
    )
    agrupados: dict[int, list[Criterio]] = {}
    for criterio in (await session.scalars(q)).all():
        agrupados.setdefault(criterio.task_id, []).append(criterio)
    return agrupados
