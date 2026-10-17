"""Consultas e escritas da nota."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Nota
from backend.repositorio import usuarios


async def _ligar_autor(session: AsyncSession, dados: dict) -> dict:
    """Resolve o texto `autor` para `autor_id`, quando der.

    Mesmo par de `task.responsavel`: o texto e o rotulo de quem nao tem
    conta, o id e o fato quando tem. Antes `autor_id` guardava QUEM CHAMOU a
    API, e isso brigava com o texto -- uma nota escrita pelo MCP em nome da
    Marina saia com `autor: "Marina Alves"` e `autor_id` apontando para a
    conta de servico. Dois campos para o mesmo conceito, discordando.

    Nome solto (ou ambiguo) deixa NULL, e ai o texto e o unico registro.
    """
    if "autor" not in dados:
        return dados
    pessoa = await usuarios.buscar_por_nome(session, dados["autor"] or "")
    return {**dados, "autor_id": pessoa.id if pessoa else None}


async def criar(session: AsyncSession, dados: dict) -> Nota:
    nota = Nota(**await _ligar_autor(session, dados))
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

    # Trocar o texto do autor reaponta a FK no mesmo commit, senao as
    # duas colunas passariam a discordar.
    campos = await _ligar_autor(session, campos)

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
