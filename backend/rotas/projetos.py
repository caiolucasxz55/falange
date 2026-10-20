"""Rotas de projeto.

`GET /projeto` responde o projeto da chamada e e aberto a quem pode `ler`:
e assim que a tela desenha o seletor e a IA confirma onde esta antes de
escrever. Listar e criar sao de admin (`gerir_projetos`).

Nao existe DELETE: apagar um projeto levaria junto task, nota, decisao,
preferencia, configuracao e autonomia. Se um dia fizer sentido, vai ser uma
acao propria e com confirmacao.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.models import SLUG_PADRAO, Projeto
from backend.repositorio import projetos as repo
from backend.schemas.projeto import ProjetoAtual, ProjetoNovo, ProjetoOut
from backend.seguranca.dependencias import (
    Chamador,
    obter_chamador,
    obter_projeto,
)

rotas = APIRouter(tags=["projetos"])


@rotas.get("/projeto", response_model=ProjetoAtual)
async def projeto_atual(
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
):
    """Em que projeto esta esta chamada."""
    chamador.exigir("ler")
    return ProjetoAtual(
        projeto=ProjetoOut.model_validate(projeto),
        padrao=projeto.slug == SLUG_PADRAO,
    )


@rotas.get("/projetos", response_model=list[ProjetoOut])
async def listar_projetos(
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("gerir_projetos")
    return await repo.listar(session)


@rotas.post("/projetos", response_model=ProjetoOut, status_code=201)
async def criar_projeto(
    novo: ProjetoNovo,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("gerir_projetos")

    if await repo.buscar_por_slug(session, novo.slug) is not None:
        raise HTTPException(409, f"ja existe projeto com o slug '{novo.slug}'")
    return await repo.criar(session, novo.model_dump())
