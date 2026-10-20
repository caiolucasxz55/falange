"""Leitura e escrita da configuracao da plataforma."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Configuracao

# Valores usados quando a chave ainda nao foi gravada.
PADROES = {"perguntas_ativas": "true"}


async def ler(session: AsyncSession, projeto_id: int) -> dict[str, str]:
    """Configuracao completa, com os padroes preenchendo o que falta."""
    q = select(Configuracao).where(Configuracao.projeto_id == projeto_id)
    linhas = (await session.scalars(q)).all()
    gravadas = {c.chave: c.valor for c in linhas}
    return {**PADROES, **gravadas}


async def definir(
    session: AsyncSession, projeto_id: int, chave: str, valor: str
) -> dict[str, str]:
    atual = await session.get(Configuracao, (projeto_id, chave))
    if atual is None:
        session.add(
            Configuracao(projeto_id=projeto_id, chave=chave, valor=valor)
        )
    else:
        atual.valor = valor
        atual.atualizada_em = func.now()
    await session.commit()
    return await ler(session, projeto_id)
