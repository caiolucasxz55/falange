"""Rotas de nota: o registro do time que nao e task."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.repositorio import notas as repo
from backend.repositorio import tasks as repo_tasks
from backend.schemas import NotaEdicao, NotaNova, NotaOut
from backend.seguranca.dependencias import Chamador, obter_chamador

rotas = APIRouter(tags=["notas"])


@rotas.post("/notas", response_model=NotaOut, status_code=201)
async def criar_nota(
    nova: NotaNova,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("criar_nota")
    if nova.task_id is not None and await repo_tasks.buscar(session, nova.task_id) is None:
        raise HTTPException(404, f"task {nova.task_id} nao encontrada")
    return await repo.criar(session, {**nova.model_dump(), "autor_id": chamador.id})


@rotas.get("/notas", response_model=list[NotaOut])
async def listar_notas(
    resolvida: Optional[bool] = None,
    task_id: Optional[int] = None,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("ler")
    return await repo.listar(session, resolvida=resolvida, task_id=task_id)


@rotas.patch("/notas/{nota_id}/resolver", response_model=NotaOut)
async def resolver_nota(
    nota_id: int,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("resolver_nota")
    nota = await repo.resolver(session, nota_id)
    if nota is None:
        raise HTTPException(404, f"nota {nota_id} nao encontrada")
    return nota


@rotas.patch("/notas/{nota_id}", response_model=NotaOut)
async def editar_nota(
    nota_id: int,
    body: NotaEdicao,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("editar_nota")
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")
    if campos.get("task_id") is not None:
        if await repo_tasks.buscar(session, campos["task_id"]) is None:
            raise HTTPException(404, f"task {campos['task_id']} nao encontrada")

    nota = await repo.editar(session, nota_id, campos)
    if nota is None:
        raise HTTPException(404, f"nota {nota_id} nao encontrada")
    return nota


@rotas.delete("/notas/{nota_id}", status_code=204, response_class=Response)
async def apagar_nota(
    nota_id: int,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    nota = await repo.buscar(session, nota_id)
    if nota is None:
        raise HTTPException(404, f"nota {nota_id} nao encontrada")
    chamador.exigir_propria("apagar_nota", nota.autor_id)

    if not await repo.remover(session, nota_id):
        raise HTTPException(404, f"nota {nota_id} nao encontrada")
