"""Rotas da configuracao da plataforma."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.repositorio import configuracao as repo
from backend.schemas import ConfiguracaoEdicao, ConfiguracaoOut
from backend.models import Projeto
from backend.seguranca.dependencias import (
    Chamador,
    obter_chamador,
    obter_projeto,
)

rotas = APIRouter(tags=["configuracao"])


def _para_saida(bruta: dict) -> ConfiguracaoOut:
    return ConfiguracaoOut(perguntas_ativas=bruta["perguntas_ativas"] == "true")


@rotas.get("/configuracao", response_model=ConfiguracaoOut)
async def ver_configuracao(
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("ler")
    return _para_saida(await repo.ler(session, projeto.id))


@rotas.patch("/configuracao", response_model=ConfiguracaoOut)
async def definir_configuracao(
    body: ConfiguracaoEdicao,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("definir_configuracao")
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")

    bruta = await repo.ler(session, projeto.id)
    for chave, valor in campos.items():
        bruta = await repo.definir(
            session, projeto.id, chave, "true" if valor else "false"
        )
    return _para_saida(bruta)
