"""Decisao, preferencia e autonomia: a memoria do Falange."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dominio.autonomia import ACOES, NIVEIS, acoes_a_rebaixar
from backend.models import (
    Autonomia,
    Decisao,
    NivelAutonomia,
    Preferencia,
    TipoAcao,
    TipoDecisao,
)


async def criar_decisao(session: AsyncSession, dados: dict) -> Decisao:
    decisao = Decisao(**dados)
    session.add(decisao)
    await rebaixar_se_preciso(session, dados)
    await session.commit()
    await session.refresh(decisao)
    return decisao


async def rebaixar_se_preciso(session: AsyncSession, decisao: dict) -> None:
    """Discordar de algo feito no automatico tira a autonomia na hora.

    Nao commita: entra no mesmo commit de quem registrou a decisao. Publica
    porque o repositorio de task tambem chama, ao detectar ajuste humano.
    """
    niveis = {
        linha.tipo_acao.value: linha.nivel.value
        for linha in (await session.scalars(select(Autonomia))).all()
    }
    for acao, novo in acoes_a_rebaixar(decisao, niveis).items():
        linha = await session.get(Autonomia, TipoAcao(acao))
        if linha is not None:
            linha.nivel = NivelAutonomia(novo)
            linha.atualizado_em = func.now()


async def listar_decisoes(
    session: AsyncSession, tipo: Optional[TipoDecisao] = None, limite: int = 500
) -> list[Decisao]:
    """Mais recentes primeiro: o habito de agora pesa mais que o de um ano."""
    q = select(Decisao).order_by(Decisao.criada_em.desc(), Decisao.id.desc())
    if tipo is not None:
        q = q.where(Decisao.tipo == tipo)
    return list((await session.scalars(q.limit(limite))).all())


async def criar_preferencia(session: AsyncSession, dados: dict) -> Preferencia:
    preferencia = Preferencia(**dados)
    session.add(preferencia)
    await session.commit()
    await session.refresh(preferencia)
    return preferencia


async def listar_preferencias(
    session: AsyncSession, ativa: Optional[bool] = None
) -> list[Preferencia]:
    q = select(Preferencia).order_by(Preferencia.id)
    if ativa is not None:
        q = q.where(Preferencia.ativa == ativa)
    return list((await session.scalars(q)).all())


async def definir_preferencia_ativa(
    session: AsyncSession, preferencia_id: int, ativa: bool
) -> Optional[Preferencia]:
    preferencia = await session.get(Preferencia, preferencia_id)
    if preferencia is None:
        return None
    preferencia.ativa = ativa
    await session.commit()
    await session.refresh(preferencia)
    return preferencia


async def ler_autonomia(session: AsyncSession) -> dict[str, str]:
    """Nivel de cada acao, com o padrao preenchendo o que nunca foi gravado."""
    linhas = (await session.scalars(select(Autonomia))).all()
    gravados = {linha.tipo_acao.value: linha.nivel.value for linha in linhas}
    return {acao: gravados.get(acao, NIVEIS[0]) for acao in ACOES}


async def definir_autonomia(
    session: AsyncSession, tipo_acao: TipoAcao, nivel: NivelAutonomia
) -> dict[str, str]:
    linha = await session.get(Autonomia, tipo_acao)
    if linha is None:
        session.add(Autonomia(tipo_acao=tipo_acao, nivel=nivel))
    else:
        linha.nivel = nivel
        linha.atualizado_em = func.now()
    await session.commit()
    return await ler_autonomia(session)
