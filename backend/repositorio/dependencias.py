"""Consultas e escritas das dependencias entre tasks.

As arestas saem daqui como tuplas `(task_id, depende_de_id)`, que e o
formato que `dominio/grafo.py` recebe: o repositorio busca, o dominio
calcula, e nenhum dos dois sabe do outro.
"""

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Dependencia, Status, Task


async def listar_arestas(
    session: AsyncSession, projeto_id: int
) -> list[tuple[int, int]]:
    """Todas as arestas do projeto.

    O grafo inteiro de uma vez, e nao por task: as contas transitivas
    (cadeia, ciclo, quem destrava quem) precisam dele completo, e buscar por
    demanda viraria uma consulta por no.
    """
    q = (
        select(Dependencia.task_id, Dependencia.depende_de_id)
        .join(Task, Task.id == Dependencia.task_id)
        .where(Task.projeto_id == projeto_id)
    )
    return [(a, b) for a, b in (await session.execute(q)).all()]


async def concluidas(session: AsyncSession, projeto_id: int) -> set[int]:
    """Ids das tasks concluidas do projeto.

    `bloqueada` e derivada disto: nao ha coluna de bloqueio para consultar.
    """
    q = select(Task.id).where(
        Task.projeto_id == projeto_id, Task.status == Status.concluida
    )
    return set((await session.scalars(q)).all())


async def existe(
    session: AsyncSession, task_id: int, depende_de_id: int
) -> bool:
    return await session.get(Dependencia, (task_id, depende_de_id)) is not None


async def adicionar(
    session: AsyncSession, task_id: int, depende_de_id: int
) -> None:
    """Grava a aresta. Quem valida (ciclo, projeto, existencia) e a rota.

    Idempotente: repetir a mesma dependencia nao e erro, so nao faz nada. A
    PK composta ja impediria a duplicata, mas estourar IntegrityError para
    quem pediu duas vezes a mesma coisa seria ruido.
    """
    if await existe(session, task_id, depende_de_id):
        return
    session.add(Dependencia(task_id=task_id, depende_de_id=depende_de_id))
    await session.commit()


async def remover(
    session: AsyncSession, task_id: int, depende_de_id: int
) -> bool:
    """False quando a aresta nao existia."""
    alvo: Optional[Dependencia] = await session.get(
        Dependencia, (task_id, depende_de_id)
    )
    if alvo is None:
        return False
    await session.delete(alvo)
    await session.commit()
    return True


async def remover_todas(session: AsyncSession, task_id: int) -> None:
    """Tira a task do grafo, nos dois sentidos. Nao commita."""
    await session.execute(
        delete(Dependencia).where(
            (Dependencia.task_id == task_id)
            | (Dependencia.depende_de_id == task_id)
        )
    )
