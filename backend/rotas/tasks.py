"""Rotas de task e de carga.

ATENCAO a ordem das rotas: `/tasks/contagem-por-bloco` tem de ser declarada
ANTES de `/tasks/{task_id}`, senao o caminho literal cai no parametro e o
FastAPI tenta ler "contagem-por-bloco" como int (422). Nao reordene.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db import get_session
from backend.models import Bloco, Origem, Prioridade, Status
from backend.repositorio import tasks as repo
from backend.schemas import (
    Bloqueio,
    Carga,
    MudancaStatus,
    TaskEdicao,
    TaskNova,
    TaskOut,
)

rotas = APIRouter(tags=["tasks"])


@rotas.post("/tasks", response_model=TaskOut, status_code=201)
async def criar_task(
    nova: TaskNova,
    session: AsyncSession = Depends(get_session),
    x_falange_fonte: Optional[str] = Header(default=None),
):
    dados = nova.model_dump()
    # Quem escreveu a task sai do header, nao do corpo: autoria declarada
    # pelo cliente seria forjavel e envenenaria calibracao e perfil.
    dados["origem"] = Origem.ia if x_falange_fonte == "mcp" else Origem.humano
    return await repo.criar(session, dados)


@rotas.get("/tasks", response_model=list[TaskOut])
async def listar_tasks(
    bloco: Optional[Bloco] = None,
    status: Optional[Status] = None,
    responsavel: Optional[str] = None,
    prioridade: Optional[Prioridade] = None,
    session: AsyncSession = Depends(get_session),
):
    return await repo.listar(
        session,
        bloco=bloco,
        status=status,
        responsavel=responsavel,
        prioridade=prioridade,
    )


@rotas.get("/tasks/contagem-por-bloco")
async def contar_tasks_por_bloco(session: AsyncSession = Depends(get_session)):
    return await repo.contagem_por_bloco(session)


@rotas.get("/carga", response_model=Carga)
async def carga(
    bloco: Optional[Bloco] = None,
    responsavel: Optional[str] = None,
    limite: Optional[int] = Query(None, description="default: LIMITE_SOBRECARGA do .env"),
    session: AsyncSession = Depends(get_session),
):
    """Quantas tasks abertas um bloco ou uma pessoa carrega, e se passou do limite."""
    if bloco is None and responsavel is None:
        raise HTTPException(400, "informe bloco ou responsavel")

    teto = limite if limite is not None else settings.limite_sobrecarga
    abertas = await repo.contar_abertas(session, bloco=bloco, responsavel=responsavel)
    return Carga(
        escopo="responsavel" if responsavel else "bloco",
        alvo=responsavel or (bloco.value if bloco else None),
        tasks_abertas=abertas,
        limite=teto,
        sobrecarregado=abertas > teto,
    )


@rotas.get("/tasks/{task_id}", response_model=TaskOut)
async def buscar_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await repo.buscar(session, task_id)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return task


@rotas.patch("/tasks/{task_id}/bloqueio", response_model=TaskOut)
async def marcar_bloqueio(
    task_id: int, body: Bloqueio, session: AsyncSession = Depends(get_session)
):
    task, erro = await repo.definir_bloqueio(session, task_id, body.bloqueada_por)
    if erro:
        raise HTTPException(404 if "nao encontrada" in erro else 409, erro)
    return task


@rotas.patch("/tasks/{task_id}/status", response_model=TaskOut)
async def mudar_status(
    task_id: int, body: MudancaStatus, session: AsyncSession = Depends(get_session)
):
    task = await repo.definir_status(session, task_id, body.status)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return task


@rotas.patch("/tasks/{task_id}", response_model=TaskOut)
async def editar_task(
    task_id: int,
    body: TaskEdicao,
    session: AsyncSession = Depends(get_session),
    # O MCP se identifica; a tela nao manda nada. E assim que o backend
    # sabe se quem corrigiu a task foi a IA ou um humano.
    x_falange_fonte: Optional[str] = Header(default=None),
):
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")
    task = await repo.editar(session, task_id, campos, fonte=x_falange_fonte)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return task


# response_class=Response: um 204 nao pode ter corpo, e sem isso o FastAPI
# ainda manda content-type: application/json, o que faz o navegador abortar.
@rotas.delete("/tasks/{task_id}", status_code=204, response_class=Response)
async def apagar_task(task_id: int, session: AsyncSession = Depends(get_session)):
    if not await repo.remover(session, task_id):
        raise HTTPException(404, f"task {task_id} nao encontrada")
