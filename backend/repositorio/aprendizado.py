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


async def criar_decisao(
    session: AsyncSession, projeto_id: int, dados: dict
) -> Decisao:
    decisao = Decisao(**{**dados, "projeto_id": projeto_id})
    session.add(decisao)
    await rebaixar_se_preciso(session, projeto_id, dados)
    await session.commit()
    await session.refresh(decisao)
    return decisao


async def rebaixar_se_preciso(
    session: AsyncSession, projeto_id: int, decisao: dict
) -> None:
    """Discordar de algo feito no automatico tira a autonomia na hora.

    Nao commita: entra no mesmo commit de quem registrou a decisao. Publica
    porque o repositorio de task tambem chama, ao detectar ajuste humano.
    """
    niveis = await ler_autonomia(session, projeto_id)
    for acao, novo in acoes_a_rebaixar(decisao, niveis).items():
        linha = await session.get(Autonomia, (projeto_id, TipoAcao(acao)))
        if linha is not None:
            linha.nivel = NivelAutonomia(novo)
            linha.atualizado_em = func.now()


async def listar_decisoes(
    session: AsyncSession,
    projeto_id: int,
    tipo: Optional[TipoDecisao] = None,
    limite: int = 500,
) -> list[Decisao]:
    """Mais recentes primeiro: o habito de agora pesa mais que o de um ano."""
    q = (
        select(Decisao)
        .where(Decisao.projeto_id == projeto_id)
        .order_by(Decisao.criada_em.desc(), Decisao.id.desc())
    )
    if tipo is not None:
        q = q.where(Decisao.tipo == tipo)
    return list((await session.scalars(q.limit(limite))).all())


async def criar_preferencia(
    session: AsyncSession, projeto_id: int, dados: dict
) -> Preferencia:
    preferencia = Preferencia(**{**dados, "projeto_id": projeto_id})
    session.add(preferencia)
    await session.commit()
    await session.refresh(preferencia)
    return preferencia


async def listar_preferencias(
    session: AsyncSession, projeto_id: int, ativa: Optional[bool] = None
) -> list[Preferencia]:
    q = (
        select(Preferencia)
        .where(Preferencia.projeto_id == projeto_id)
        .order_by(Preferencia.id)
    )
    if ativa is not None:
        q = q.where(Preferencia.ativa == ativa)
    return list((await session.scalars(q)).all())


async def definir_preferencia_ativa(
    session: AsyncSession, projeto_id: int, preferencia_id: int, ativa: bool
) -> Optional[Preferencia]:
    preferencia = await session.get(Preferencia, preferencia_id)
    if preferencia is None or preferencia.projeto_id != projeto_id:
        return None
    preferencia.ativa = ativa
    await session.commit()
    await session.refresh(preferencia)
    return preferencia


async def ler_autonomia(session: AsyncSession, projeto_id: int) -> dict[str, str]:
    """Nivel de cada acao, com o padrao preenchendo o que nunca foi gravado."""
    q = select(Autonomia).where(Autonomia.projeto_id == projeto_id)
    linhas = (await session.scalars(q)).all()
    gravados = {linha.tipo_acao.value: linha.nivel.value for linha in linhas}
    return {acao: gravados.get(acao, NIVEIS[0]) for acao in ACOES}


async def definir_autonomia(
    session: AsyncSession,
    projeto_id: int,
    tipo_acao: TipoAcao,
    nivel: NivelAutonomia,
) -> dict[str, str]:
    linha = await session.get(Autonomia, (projeto_id, tipo_acao))
    if linha is None:
        session.add(
            Autonomia(projeto_id=projeto_id, tipo_acao=tipo_acao, nivel=nivel)
        )
    else:
        linha.nivel = nivel
        linha.atualizado_em = func.now()
    await session.commit()
    return await ler_autonomia(session, projeto_id)
