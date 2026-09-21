"""API HTTP do Falange V1.

Sem estado proprio: tudo vive no Postgres. Esta camada so traduz HTTP
em chamadas do crud. Os servidores MCP falam com o mundo por AQUI, nunca
direto com o banco -- uma fonte de verdade so.
"""

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from backend import crud
from backend.db import get_session
from backend.models import Bloco, Status
from backend.schemas import (
    Bloqueio,
    Carga,
    MudancaStatus,
    TaskEdicao,
    TaskNova,
    TaskOut,
)
from backend.config import settings

app = FastAPI(title="Falange V1")

# Sem isso o navegador bloqueia as chamadas do frontend (outra origem/porta).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    return {"status": "ok", **(await crud.contagem_por_bloco(session))}


@app.post("/tasks", response_model=TaskOut, status_code=201)
async def criar_task(nova: TaskNova, session: AsyncSession = Depends(get_session)):
    return await crud.criar(session, nova.model_dump())


@app.get("/tasks", response_model=list[TaskOut])
async def listar_tasks(
    bloco: Optional[Bloco] = None,
    status: Optional[Status] = None,
    responsavel: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    return await crud.listar(session, bloco=bloco, status=status, responsavel=responsavel)


@app.get("/tasks/contagem-por-bloco")
async def contar_tasks_por_bloco(session: AsyncSession = Depends(get_session)):
    return await crud.contagem_por_bloco(session)


@app.get("/carga", response_model=Carga)
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
    abertas = await crud.contar_abertas(session, bloco=bloco, responsavel=responsavel)
    return Carga(
        escopo="responsavel" if responsavel else "bloco",
        alvo=responsavel or (bloco.value if bloco else None),
        tasks_abertas=abertas,
        limite=teto,
        sobrecarregado=abertas > teto,
    )


@app.get("/tasks/{task_id}", response_model=TaskOut)
async def buscar_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await crud.buscar(session, task_id)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return task


@app.patch("/tasks/{task_id}/bloqueio", response_model=TaskOut)
async def marcar_bloqueio(
    task_id: int, body: Bloqueio, session: AsyncSession = Depends(get_session)
):
    task, erro = await crud.definir_bloqueio(session, task_id, body.bloqueada_por)
    if erro:
        raise HTTPException(404 if "nao encontrada" in erro else 409, erro)
    return task


@app.patch("/tasks/{task_id}/status", response_model=TaskOut)
async def mudar_status(
    task_id: int, body: MudancaStatus, session: AsyncSession = Depends(get_session)
):
    task = await crud.definir_status(session, task_id, body.status)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return task


@app.patch("/tasks/{task_id}", response_model=TaskOut)
async def editar_task(
    task_id: int, body: TaskEdicao, session: AsyncSession = Depends(get_session)
):
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")
    task = await crud.editar(session, task_id, campos)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return task


@app.delete("/tasks/{task_id}", status_code=204)
async def apagar_task(task_id: int, session: AsyncSession = Depends(get_session)):
    if not await crud.remover(session, task_id):
        raise HTTPException(404, f"task {task_id} nao encontrada")
