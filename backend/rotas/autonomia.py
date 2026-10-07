"""Rotas de autonomia: quanto a IA pode fazer sozinha."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.dominio.autonomia import DECISAO_POR_ACAO, e_promocao
from backend.dominio.autonomia import montar as montar_autonomia
from backend.models import TipoAcao, TipoDecisao
from backend.repositorio import aprendizado as repo
from backend.schemas import AutonomiaEdicao, DecisaoOut
from backend.seguranca.dependencias import Chamador, obter_chamador

rotas = APIRouter(tags=["autonomia"])


@rotas.get("/autonomia")
async def ver_autonomia(
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    """Nivel de cada acao e se o historico ja permite promover."""
    chamador.exigir("ler")
    niveis = await repo.ler_autonomia(session)
    decisoes_por_tipo: dict[str, list[dict]] = {}
    for tipo in {t for t in DECISAO_POR_ACAO.values() if t}:
        decisoes_por_tipo[tipo] = [
            DecisaoOut.model_validate(d).model_dump()
            for d in await repo.listar_decisoes(session, tipo=TipoDecisao(tipo))
        ]
    return montar_autonomia(niveis, decisoes_por_tipo)


@rotas.patch("/autonomia/{tipo_acao}")
async def definir_autonomia(
    tipo_acao: TipoAcao,
    body: AutonomiaEdicao,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    """Muda o nivel de uma acao.

    Subir exige papel; descer e livre para quem trabalha, inclusive para a
    IA. A assimetria e a mesma de sempre: perder confianca e seguro.
    """
    atuais = await repo.ler_autonomia(session)
    sobe = e_promocao(atuais.get(tipo_acao.value, "perguntar"), body.nivel.value)
    chamador.exigir("promover_autonomia" if sobe else "rebaixar_autonomia")

    niveis = await repo.definir_autonomia(session, tipo_acao, body.nivel)
    return {"acoes": niveis}
