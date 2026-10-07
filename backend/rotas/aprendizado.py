"""Rotas de decisao, preferencia e perfil: o que o Falange aprende."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.dominio.calibracao import calibrar
from backend.dominio.perfil import montar as montar_perfil
from backend.models import OrigemPreferencia, Status, TipoDecisao
from backend.repositorio import aprendizado as repo
from backend.repositorio import tasks as repo_tasks
from backend.schemas import (
    DecisaoNova,
    DecisaoOut,
    PreferenciaEdicao,
    PreferenciaNova,
    PreferenciaOut,
    TaskOut,
)
from backend.seguranca.dependencias import Chamador, obter_chamador

rotas = APIRouter(tags=["aprendizado"])


@rotas.post("/decisoes", response_model=DecisaoOut, status_code=201)
async def registrar_decisao(
    nova: DecisaoNova,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("registrar_decisao")
    if nova.task_id is not None and await repo_tasks.buscar(session, nova.task_id) is None:
        raise HTTPException(404, f"task {nova.task_id} nao encontrada")
    return await repo.criar_decisao(
        session, {**nova.model_dump(), "autor_id": chamador.id}
    )


@rotas.get("/decisoes", response_model=list[DecisaoOut])
async def listar_decisoes(
    tipo: Optional[TipoDecisao] = None,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("ler")
    return await repo.listar_decisoes(session, tipo=tipo)


@rotas.post("/preferencias", response_model=PreferenciaOut, status_code=201)
async def registrar_preferencia(
    nova: PreferenciaNova,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    """Explicita nasce ativa; inferida nasce inativa e espera confirmacao.

    Nascer ativa exige o papel de quem pode ATIVAR: a IA nao cria regra que
    ela mesma vai obedecer, e um dev tambem nao liga regra para o time.
    Nos dois casos a preferencia nasce inativa e espera confirmacao na tela.
    """
    chamador.exigir("criar_preferencia")
    dados = nova.model_dump()
    dados["ativa"] = nova.origem is OrigemPreferencia.explicita and chamador.pode(
        "ativar_preferencia"
    )
    return await repo.criar_preferencia(session, dados)


@rotas.get("/preferencias", response_model=list[PreferenciaOut])
async def listar_preferencias(
    ativa: Optional[bool] = None,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("ler")
    return await repo.listar_preferencias(session, ativa=ativa)


@rotas.patch("/preferencias/{preferencia_id}", response_model=PreferenciaOut)
async def definir_preferencia(
    preferencia_id: int,
    body: PreferenciaEdicao,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    """Ativa (confirmar) ou desativa.

    Desativar e livre para quem registra preferencia: desligar uma regra nao
    aumenta a confianca em ninguem. Ativar exige papel.
    """
    if body.ativa:
        chamador.exigir("ativar_preferencia")
    else:
        chamador.exigir("criar_preferencia")
    preferencia = await repo.definir_preferencia_ativa(
        session, preferencia_id, body.ativa
    )
    if preferencia is None:
        raise HTTPException(404, f"preferencia {preferencia_id} nao encontrada")
    return preferencia


@rotas.get("/perfil")
async def perfil(
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    """O que o Falange aprendeu: calibracao, aceitacao, correcoes e padroes."""
    chamador.exigir("ler")
    decisoes = [
        DecisaoOut.model_validate(d).model_dump()
        for d in await repo.listar_decisoes(session)
    ]
    preferencias = [
        PreferenciaOut.model_validate(p).model_dump()
        for p in await repo.listar_preferencias(session)
    ]
    concluidas = await repo_tasks.listar(session, status=Status.concluida)
    calibracao = calibrar([TaskOut.model_validate(t).model_dump() for t in concluidas])
    return montar_perfil(decisoes, preferencias, calibracao)
