"""Rotas de autonomia: quanto a IA pode fazer sozinha."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.dominio.autonomia import DECISAO_POR_ACAO, e_promocao
from backend.dominio.autonomia import montar as montar_autonomia
from backend.models import TipoAcao, TipoDecisao
from backend.repositorio import aprendizado as repo
from backend.schemas import AutonomiaEdicao, DecisaoOut
from backend.seguranca import pode_elevar

rotas = APIRouter(tags=["autonomia"])


@rotas.get("/autonomia")
async def ver_autonomia(session: AsyncSession = Depends(get_session)):
    """Nivel de cada acao e se o historico ja permite promover."""
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
    session: AsyncSession = Depends(get_session),
    x_falange_fonte: Optional[str] = Header(default=None),
):
    """Muda o nivel de uma acao. Subir e decisao do humano, nunca da IA."""
    atuais = await repo.ler_autonomia(session)
    sobe = e_promocao(atuais.get(tipo_acao.value, "perguntar"), body.nivel.value)
    if sobe and not pode_elevar(x_falange_fonte):
        raise HTTPException(
            403,
            "promover autonomia so fora do MCP: peca ao dev para subir na tela",
        )
    niveis = await repo.definir_autonomia(session, tipo_acao, body.nivel)
    return {"acoes": niveis}
