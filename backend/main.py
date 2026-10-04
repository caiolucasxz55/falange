"""API HTTP do Falange V1.

Sem estado proprio: tudo vive no Postgres. Esta camada so traduz HTTP
em chamadas do crud. Os servidores MCP falam com o mundo por AQUI, nunca
direto com o banco -- uma fonte de verdade so.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from backend import crud
from backend.autonomia import DECISAO_POR_ACAO
from backend.autonomia import montar as montar_autonomia
from backend.calibracao import calibrar
from backend.perfil import montar as montar_perfil
from backend.priorizacao import ranquear
from backend.db import get_session
from backend.models import (
    Bloco,
    NivelAutonomia,
    OrigemPreferencia,
    Prioridade,
    Status,
    TipoAcao,
    TipoDecisao,
)
from backend.schemas import (
    AutonomiaEdicao,
    Bloqueio,
    Carga,
    DecisaoNova,
    DecisaoOut,
    PreferenciaEdicao,
    PreferenciaNova,
    PreferenciaOut,
    ConfiguracaoEdicao,
    ConfiguracaoOut,
    MudancaStatus,
    NotaEdicao,
    NotaNova,
    NotaOut,
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
    prioridade: Optional[Prioridade] = None,
    session: AsyncSession = Depends(get_session),
):
    return await crud.listar(
        session,
        bloco=bloco,
        status=status,
        responsavel=responsavel,
        prioridade=prioridade,
    )


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
    task = await crud.editar(session, task_id, campos, fonte=x_falange_fonte)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return task


# response_class=Response: um 204 nao pode ter corpo, e sem isso o FastAPI
# ainda manda content-type: application/json, o que faz o navegador abortar.
@app.delete("/tasks/{task_id}", status_code=204, response_class=Response)
async def apagar_task(task_id: int, session: AsyncSession = Depends(get_session)):
    if not await crud.remover(session, task_id):
        raise HTTPException(404, f"task {task_id} nao encontrada")


# --------------------------------------------------------------------------
# notas: registro solto do time, sem virar task
# --------------------------------------------------------------------------


@app.post("/notas", response_model=NotaOut, status_code=201)
async def criar_nota(nova: NotaNova, session: AsyncSession = Depends(get_session)):
    if nova.task_id is not None and await crud.buscar(session, nova.task_id) is None:
        raise HTTPException(404, f"task {nova.task_id} nao encontrada")
    return await crud.criar_nota(session, nova.model_dump())


@app.get("/notas", response_model=list[NotaOut])
async def listar_notas(
    resolvida: Optional[bool] = None,
    task_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    return await crud.listar_notas(session, resolvida=resolvida, task_id=task_id)


@app.patch("/notas/{nota_id}/resolver", response_model=NotaOut)
async def resolver_nota(nota_id: int, session: AsyncSession = Depends(get_session)):
    nota = await crud.resolver_nota(session, nota_id)
    if nota is None:
        raise HTTPException(404, f"nota {nota_id} nao encontrada")
    return nota


@app.patch("/notas/{nota_id}", response_model=NotaOut)
async def editar_nota(
    nota_id: int, body: NotaEdicao, session: AsyncSession = Depends(get_session)
):
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")
    if campos.get("task_id") is not None:
        if await crud.buscar(session, campos["task_id"]) is None:
            raise HTTPException(404, f"task {campos['task_id']} nao encontrada")

    nota = await crud.editar_nota(session, nota_id, campos)
    if nota is None:
        raise HTTPException(404, f"nota {nota_id} nao encontrada")
    return nota


@app.delete("/notas/{nota_id}", status_code=204, response_class=Response)
async def apagar_nota(nota_id: int, session: AsyncSession = Depends(get_session)):
    if not await crud.remover_nota(session, nota_id):
        raise HTTPException(404, f"nota {nota_id} nao encontrada")


# --------------------------------------------------------------------------
# priorizacao: o que vale a pena fazer agora
# --------------------------------------------------------------------------


@app.get("/priorizacao")
async def priorizacao(
    responsavel: Optional[str] = None,
    bloco: Optional[Bloco] = None,
    limite: int = Query(5, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """Ranking explicado das tasks que dao para pegar agora.

    O ranking roda sobre TODAS as tasks: a cadeia de bloqueio e global, e
    filtrar antes quebraria a conta de quem destrava quem. O filtro de bloco
    se aplica depois, so nas sugestoes.
    """
    tasks = [
        TaskOut.model_validate(t).model_dump()
        for t in await crud.listar(session)
    ]

    # Carga so de quem aparece como responsavel: alimenta o aviso de sobrecarga.
    cargas = {}
    for nome in {t["responsavel"] for t in tasks if t["responsavel"]}:
        abertas = await crud.contar_abertas(session, responsavel=nome)
        cargas[nome] = {
            "tasks_abertas": abertas,
            "limite": settings.limite_sobrecarga,
            "sobrecarregado": abertas > settings.limite_sobrecarga,
        }

    saida = ranquear(tasks, datetime.now(timezone.utc), cargas, responsavel)

    if bloco is not None:
        saida["sugestoes"] = [s for s in saida["sugestoes"] if s["bloco"] == bloco.value]
    saida["sugestoes"] = saida["sugestoes"][:limite]
    return saida


@app.get("/calibracao")
async def calibracao(session: AsyncSession = Depends(get_session)):
    """Compara a estimativa com a duracao real das tasks ja concluidas.

    So entram tasks com os dois marcos de tempo; o resto nao da para medir.
    """
    concluidas = await crud.listar(session, status=Status.concluida)
    return calibrar([TaskOut.model_validate(t).model_dump() for t in concluidas])


# --------------------------------------------------------------------------
# configuracao: comportamento da plataforma
# --------------------------------------------------------------------------


def _para_saida(bruta: dict) -> ConfiguracaoOut:
    return ConfiguracaoOut(perguntas_ativas=bruta["perguntas_ativas"] == "true")


@app.get("/configuracao", response_model=ConfiguracaoOut)
async def ver_configuracao(session: AsyncSession = Depends(get_session)):
    return _para_saida(await crud.ler_configuracao(session))


@app.patch("/configuracao", response_model=ConfiguracaoOut)
async def definir_configuracao(
    body: ConfiguracaoEdicao, session: AsyncSession = Depends(get_session)
):
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")

    bruta = await crud.ler_configuracao(session)
    for chave, valor in campos.items():
        bruta = await crud.definir_configuracao(
            session, chave, "true" if valor else "false"
        )
    return _para_saida(bruta)


# --------------------------------------------------------------------------
# aprendizado: decisoes, preferencias e perfil
# --------------------------------------------------------------------------


@app.post("/decisoes", response_model=DecisaoOut, status_code=201)
async def registrar_decisao(
    nova: DecisaoNova, session: AsyncSession = Depends(get_session)
):
    if nova.task_id is not None and await crud.buscar(session, nova.task_id) is None:
        raise HTTPException(404, f"task {nova.task_id} nao encontrada")
    return await crud.criar_decisao(session, nova.model_dump())


@app.get("/decisoes", response_model=list[DecisaoOut])
async def listar_decisoes(
    tipo: Optional[TipoDecisao] = None,
    session: AsyncSession = Depends(get_session),
):
    return await crud.listar_decisoes(session, tipo=tipo)


@app.post("/preferencias", response_model=PreferenciaOut, status_code=201)
async def registrar_preferencia(
    nova: PreferenciaNova, session: AsyncSession = Depends(get_session)
):
    """Explicita nasce ativa; inferida nasce inativa e espera confirmacao."""
    dados = nova.model_dump()
    dados["ativa"] = nova.origem is OrigemPreferencia.explicita
    return await crud.criar_preferencia(session, dados)


@app.get("/preferencias", response_model=list[PreferenciaOut])
async def listar_preferencias(
    ativa: Optional[bool] = None, session: AsyncSession = Depends(get_session)
):
    return await crud.listar_preferencias(session, ativa=ativa)


@app.patch("/preferencias/{preferencia_id}", response_model=PreferenciaOut)
async def definir_preferencia(
    preferencia_id: int,
    body: PreferenciaEdicao,
    session: AsyncSession = Depends(get_session),
):
    """Ativa (confirmar) ou desativa. Desativar e sempre permitido."""
    preferencia = await crud.definir_preferencia_ativa(
        session, preferencia_id, body.ativa
    )
    if preferencia is None:
        raise HTTPException(404, f"preferencia {preferencia_id} nao encontrada")
    return preferencia


@app.get("/perfil")
async def perfil(session: AsyncSession = Depends(get_session)):
    """O que o Falange aprendeu: calibracao, aceitacao, correcoes e padroes."""
    decisoes = [
        DecisaoOut.model_validate(d).model_dump()
        for d in await crud.listar_decisoes(session)
    ]
    preferencias = [
        PreferenciaOut.model_validate(p).model_dump()
        for p in await crud.listar_preferencias(session)
    ]
    concluidas = await crud.listar(session, status=Status.concluida)
    calibracao = calibrar([TaskOut.model_validate(t).model_dump() for t in concluidas])
    return montar_perfil(decisoes, preferencias, calibracao)


# --------------------------------------------------------------------------
# autonomia: quanto a IA pode fazer sozinha
# --------------------------------------------------------------------------


@app.get("/autonomia")
async def ver_autonomia(session: AsyncSession = Depends(get_session)):
    """Nivel de cada acao e se o historico ja permite promover."""
    niveis = await crud.ler_autonomia(session)
    decisoes_por_tipo: dict[str, list[dict]] = {}
    for tipo in {t for t in DECISAO_POR_ACAO.values() if t}:
        decisoes_por_tipo[tipo] = [
            DecisaoOut.model_validate(d).model_dump()
            for d in await crud.listar_decisoes(session, tipo=TipoDecisao(tipo))
        ]
    return montar_autonomia(niveis, decisoes_por_tipo)


@app.patch("/autonomia/{tipo_acao}")
async def definir_autonomia(
    tipo_acao: TipoAcao,
    body: AutonomiaEdicao,
    session: AsyncSession = Depends(get_session),
):
    """Muda o nivel de uma acao. Subir e decisao do humano, nunca da IA."""
    niveis = await crud.definir_autonomia(session, tipo_acao, body.nivel)
    return {"acoes": niveis}
