"""Leitura e escrita da configuracao da plataforma."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Configuracao

# Valores usados quando a chave ainda nao foi gravada.
PADROES = {"perguntas_ativas": "true"}


async def ler(session: AsyncSession) -> dict[str, str]:
    """Configuracao completa, com os padroes preenchendo o que falta."""
    linhas = (await session.scalars(select(Configuracao))).all()
    gravadas = {c.chave: c.valor for c in linhas}
    return {**PADROES, **gravadas}


async def definir(session: AsyncSession, chave: str, valor: str) -> dict[str, str]:
    atual = await session.get(Configuracao, chave)
    if atual is None:
        session.add(Configuracao(chave=chave, valor=valor))
    else:
        atual.valor = valor
        atual.atualizada_em = func.now()
    await session.commit()
    return await ler(session)
