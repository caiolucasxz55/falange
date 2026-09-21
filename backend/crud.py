"""Consultas. Toda regra de banco mora aqui; main.py so faz HTTP."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import ABERTAS, Bloco, Status, Task


async def criar(session: AsyncSession, dados: dict) -> Task:
    task = Task(**dados)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def buscar(session: AsyncSession, task_id: int) -> Optional[Task]:
    return await session.get(Task, task_id)


async def listar(
    session: AsyncSession,
    bloco: Optional[Bloco] = None,
    status: Optional[Status] = None,
    responsavel: Optional[str] = None,
) -> list[Task]:
    q = select(Task).order_by(Task.id)
    if bloco is not None:
        q = q.where(Task.bloco == bloco)
    if status is not None:
        q = q.where(Task.status == status)
    if responsavel is not None:
        q = q.where(Task.responsavel == responsavel)
    return list((await session.scalars(q)).all())


async def _criaria_ciclo(session: AsyncSession, task_id: int, alvo_id: int) -> bool:
    """Anda a cadeia de bloqueio a partir de alvo_id procurando voltar em task_id."""
    visitados: set[int] = set()
    atual: Optional[int] = alvo_id
    while atual is not None:
        if atual == task_id:
            return True
        if atual in visitados:
            return False
        visitados.add(atual)
        t = await session.get(Task, atual)
        atual = t.bloqueada_por if t else None
    return False


async def definir_bloqueio(
    session: AsyncSession, task_id: int, bloqueada_por: Optional[int]
) -> tuple[Optional[Task], Optional[str]]:
    """Retorna (task, erro). Recusa auto-bloqueio e ciclos."""
    task = await session.get(Task, task_id)
    if task is None:
        return None, f"task {task_id} nao encontrada"

    if bloqueada_por is not None:
        if bloqueada_por == task_id:
            return None, "uma task nao pode bloquear a si mesma"
        if await session.get(Task, bloqueada_por) is None:
            return None, f"task bloqueadora {bloqueada_por} nao encontrada"
        if await _criaria_ciclo(session, task_id, bloqueada_por):
            return None, (
                f"bloquear {task_id} por {bloqueada_por} criaria um ciclo de dependencia"
            )

    task.bloqueada_por = bloqueada_por
    await session.commit()
    await session.refresh(task)
    return task, None


async def definir_status(
    session: AsyncSession, task_id: int, status: Status
) -> Optional[Task]:
    task = await session.get(Task, task_id)
    if task is None:
        return None
    task.status = status
    # Task concluida nao fica pendurada em bloqueio: o fato deixou de valer.
    if status is Status.concluida:
        task.bloqueada_por = None
    await session.commit()
    await session.refresh(task)
    return task


async def contagem_por_bloco(session: AsyncSession) -> dict:
    q = select(Task.bloco, func.count(Task.id)).group_by(Task.bloco)
    bruto = {bloco.value: n for bloco, n in (await session.execute(q)).all()}
    por_bloco = {b.value: bruto.get(b.value, 0) for b in Bloco}
    return {"total": sum(por_bloco.values()), "por_bloco": por_bloco}


async def contar_abertas(
    session: AsyncSession,
    bloco: Optional[Bloco] = None,
    responsavel: Optional[str] = None,
) -> int:
    q = select(func.count(Task.id)).where(Task.status.in_(ABERTAS))
    if bloco is not None:
        q = q.where(Task.bloco == bloco)
    if responsavel is not None:
        q = q.where(Task.responsavel == responsavel)
    return int((await session.execute(q)).scalar_one())


async def editar(
    session: AsyncSession, task_id: int, campos: dict
) -> Optional[Task]:
    """Altera apenas os campos presentes em `campos`."""
    task = await session.get(Task, task_id)
    if task is None:
        return None
    for campo, valor in campos.items():
        setattr(task, campo, valor)
    await session.commit()
    await session.refresh(task)
    return task


async def remover(session: AsyncSession, task_id: int) -> bool:
    """Remove a task. Quem dependia dela fica com bloqueada_por = NULL
    (ON DELETE SET NULL), entao ninguem sobra apontando para um id morto."""
    task = await session.get(Task, task_id)
    if task is None:
        return False
    await session.delete(task)
    await session.commit()
    return True
