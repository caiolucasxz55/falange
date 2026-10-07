"""Rotas da configuracao da plataforma."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.repositorio import configuracao as repo
from backend.schemas import ConfiguracaoEdicao, ConfiguracaoOut

rotas = APIRouter(tags=["configuracao"])


def _para_saida(bruta: dict) -> ConfiguracaoOut:
    return ConfiguracaoOut(perguntas_ativas=bruta["perguntas_ativas"] == "true")


@rotas.get("/configuracao", response_model=ConfiguracaoOut)
async def ver_configuracao(session: AsyncSession = Depends(get_session)):
    return _para_saida(await repo.ler(session))


@rotas.patch("/configuracao", response_model=ConfiguracaoOut)
async def definir_configuracao(
    body: ConfiguracaoEdicao, session: AsyncSession = Depends(get_session)
):
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")

    bruta = await repo.ler(session)
    for chave, valor in campos.items():
        bruta = await repo.definir(session, chave, "true" if valor else "false")
    return _para_saida(bruta)
