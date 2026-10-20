"""Consultas de projeto.

Nao existe remocao: apagar um projeto levaria junto task, nota, decisao,
preferencia, configuracao e autonomia (CASCADE). Se um dia isso fizer
sentido, vai ser uma acao propria e com confirmacao, nao um DELETE comum.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Projeto, SLUG_PADRAO


def normalizar_slug(slug: str) -> str:
    return (slug or "").strip().lower()


async def buscar(session: AsyncSession, projeto_id: int) -> Optional[Projeto]:
    return await session.get(Projeto, projeto_id)


async def buscar_por_slug(session: AsyncSession, slug: str) -> Optional[Projeto]:
    limpo = normalizar_slug(slug)
    if not limpo:
        return None
    q = select(Projeto).where(Projeto.slug == limpo)
    return (await session.scalars(q)).first()


async def buscar_padrao(session: AsyncSession) -> Optional[Projeto]:
    """O projeto que recebe quem nao diz em qual esta.

    Criado pela migration 0008. Ausente significa banco nao migrado, e quem
    chama transforma isso num erro claro em vez de num AttributeError.
    """
    return await buscar_por_slug(session, SLUG_PADRAO)


async def listar(session: AsyncSession) -> list[Projeto]:
    q = select(Projeto).order_by(Projeto.nome, Projeto.id)
    return list((await session.scalars(q)).all())


async def criar(session: AsyncSession, dados: dict) -> Projeto:
    projeto = Projeto(**{**dados, "slug": normalizar_slug(dados["slug"])})
    session.add(projeto)
    await session.commit()
    await session.refresh(projeto)
    return projeto
