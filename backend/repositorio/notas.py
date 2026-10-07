"""Consultas e escritas da nota."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Nota


async def criar(session: AsyncSession, dados: dict) -> Nota:
    nota = Nota(**dados)
    session.add(nota)
    await session.commit()
    await session.refresh(nota)
    return nota


async def buscar(session: AsyncSession, nota_id: int) -> Optional[Nota]:
    return await session.get(Nota, nota_id)


async def listar(
    session: AsyncSession,
    resolvida: Optional[bool] = None,
    task_id: Optional[int] = None,
) -> list[Nota]:
    """Mais recentes primeiro: nota nova e a que interessa."""
    q = select(Nota).order_by(Nota.criada_em.desc(), Nota.id.desc())
    if resolvida is not None:
        q = q.where(Nota.resolvida == resolvida)
    if task_id is not None:
        q = q.where(Nota.task_id == task_id)
    return list((await session.scalars(q)).all())


async def resolver(session: AsyncSession, nota_id: int) -> Optional[Nota]:
    nota = await session.get(Nota, nota_id)
    if nota is None:
        return None
    nota.resolvida = True
    await session.commit()
    await session.refresh(nota)
    return nota


async def editar(session: AsyncSession, nota_id: int, campos: dict) -> Optional[Nota]:
    """Altera apenas os campos presentes em `campos`."""
    nota = await session.get(Nota, nota_id)
    if nota is None:
        return None
    for campo, valor in campos.items():
        setattr(nota, campo, valor)
    await session.commit()
    await session.refresh(nota)
    return nota


async def remover(session: AsyncSession, nota_id: int) -> bool:
    nota = await session.get(Nota, nota_id)
    if nota is None:
        return False
    await session.delete(nota)
    await session.commit()
    return True
