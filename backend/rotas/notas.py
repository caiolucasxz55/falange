"""Rotas de nota: o registro do time que nao e task."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.dominio.papeis import assinatura_da_nota
from backend.repositorio import notas as repo
from backend.repositorio import tasks as repo_tasks
from backend.schemas import NotaEdicao, NotaNova, NotaOut
from backend.models import Projeto
from backend.seguranca.dependencias import (
    Chamador,
    obter_chamador,
    obter_projeto,
)

rotas = APIRouter(tags=["notas"])


@rotas.post("/notas", response_model=NotaOut, status_code=201)
async def criar_nota(
    nova: NotaNova,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("criar_nota")
    if nova.task_id is not None:
        if await repo_tasks.buscar(session, projeto.id, nova.task_id) is None:
            if await repo_tasks.existe_em_outro_projeto(
                session, projeto.id, nova.task_id
            ):
                raise HTTPException(
                    409, f"task {nova.task_id} e de outro projeto"
                )
            raise HTTPException(404, f"task {nova.task_id} nao encontrada")

    dados = nova.model_dump()
    dados["autor"] = assinatura_da_nota(
        chamador.nome, chamador.e_ia, dados.get("autor")
    )
    dados["projeto_id"] = projeto.id
    return await repo.criar(session, dados)


@rotas.get("/notas", response_model=list[NotaOut])
async def listar_notas(
    resolvida: Optional[bool] = None,
    task_id: Optional[int] = None,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("ler")
    return await repo.listar(
        session, projeto.id, resolvida=resolvida, task_id=task_id
    )


@rotas.patch("/notas/{nota_id}/resolver", response_model=NotaOut)
async def resolver_nota(
    nota_id: int,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("resolver_nota")
    nota = await repo.resolver(session, projeto.id, nota_id)
    if nota is None:
        raise HTTPException(404, f"nota {nota_id} nao encontrada")
    return nota


@rotas.patch("/notas/{nota_id}", response_model=NotaOut)
async def editar_nota(
    nota_id: int,
    body: NotaEdicao,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("editar_nota")
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")
    if campos.get("task_id") is not None:
        alvo = campos["task_id"]
        if await repo_tasks.buscar(session, projeto.id, alvo) is None:
            if await repo_tasks.existe_em_outro_projeto(session, projeto.id, alvo):
                raise HTTPException(409, f"task {alvo} e de outro projeto")
            raise HTTPException(404, f"task {alvo} nao encontrada")

    nota = await repo.editar(session, projeto.id, nota_id, campos)
    if nota is None:
        raise HTTPException(404, f"nota {nota_id} nao encontrada")
    return nota


@rotas.delete("/notas/{nota_id}", status_code=204, response_class=Response)
async def apagar_nota(
    nota_id: int,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    nota = await repo.buscar(session, projeto.id, nota_id)
    if nota is None:
        raise HTTPException(404, f"nota {nota_id} nao encontrada")
    chamador.exigir_propria("apagar_nota", nota.autor_id)

    if not await repo.remover(session, projeto.id, nota_id):
        raise HTTPException(404, f"nota {nota_id} nao encontrada")
