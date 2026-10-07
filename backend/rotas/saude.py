"""Healthcheck.

Fica fora do token e fora do rate limit: o docker precisa dele antes de
qualquer configuracao. Em troca, expoe contagem de task sem autenticacao --
decisao consciente, registrada no README.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.repositorio import tasks as repo

rotas = APIRouter(tags=["saude"])


@rotas.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    return {"status": "ok", **(await repo.contagem_por_bloco(session))}
