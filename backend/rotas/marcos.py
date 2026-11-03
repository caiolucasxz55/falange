"""Rotas de marco: a entrega com data, e a previsao de prazo dela.

ATENCAO a ordem: `/marcos/previsao` tem de ficar declarada ANTES de
`/marcos/{marco_id}`, senao o caminho literal cai no parametro e o FastAPI
tenta ler "previsao" como int (422). E a mesma pegadinha de
`/tasks/contagem-por-bloco` em `rotas/tasks.py`. Nao reordene.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.dominio import previsao as dom_previsao
from backend.dominio.calibracao import calibrar
from backend.models import Projeto, Status
from backend.repositorio import marcos as repo
from backend.repositorio import tasks as repo_tasks
from backend.schemas import TaskOut
from backend.schemas.marco import (
    FechamentoMarco,
    MarcoComPrevisao,
    MarcoEdicao,
    MarcoNovo,
    MarcoOut,
)
from backend.seguranca.dependencias import (
    Chamador,
    obter_chamador,
    obter_projeto,
)

rotas = APIRouter(tags=["marcos"])


async def _calibracao_do_projeto(session: AsyncSession, projeto_id: int) -> dict:
    """A mesma calibracao que a IA consulta antes de estimar.

    Previsao e estimativa tem de falar do mesmo numero: se o painel usasse
    uma media propria, ele contradiria a conversa com a IA sobre a mesma
    task, e ninguem saberia qual acreditar.
    """
    concluidas = await repo_tasks.listar(
        session, projeto_id, status=Status.concluida
    )
    return calibrar([TaskOut.model_validate(t).model_dump() for t in concluidas])


@rotas.get("/marcos", response_model=list[MarcoOut])
async def listar_marcos(
    incluir_fechados: bool = True,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("ler")
    return await repo.listar(session, projeto.id, incluir_fechados)


@rotas.get("/marcos/previsao", response_model=list[MarcoComPrevisao])
async def previsao_dos_marcos(
    incluir_fechados: bool = False,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Todos os marcos com o veredito de prazo e a conta que o sustenta.

    Fechados ficam de fora por padrao: a pergunta "o que esta em risco" e
    sobre o que ainda nao foi entregue.
    """
    chamador.exigir("ler")

    lista = await repo.listar(session, projeto.id, incluir_fechados)
    # Uma consulta para as tasks de todos os marcos, e uma para a
    # calibracao. Por marco seria N+1 numa tela que mostra todos.
    por_marco = await repo.tasks_por_marco(session, projeto.id)
    calibracao = await _calibracao_do_projeto(session, projeto.id)

    saida = []
    for marco in lista:
        tasks = [
            TaskOut.model_validate(t).model_dump()
            for t in por_marco.get(marco.id, [])
        ]
        com_previsao = MarcoComPrevisao.model_validate(
            marco, from_attributes=True
        )
        com_previsao.previsao = dom_previsao.prever(
            {
                "nome": marco.nome,
                "data_alvo": marco.data_alvo,
                "fechado_em": marco.fechado_em,
            },
            tasks,
            calibracao,
        )
        saida.append(com_previsao)
    return saida


@rotas.post("/marcos", response_model=MarcoOut, status_code=201)
async def criar_marco(
    body: MarcoNovo,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Cria um marco. So admin e lead.

    A IA NAO cria marco, de proposito: um marco e um compromisso de
    entrega com data, e isso nao e transcricao de pedido -- e decisao de
    quem responde pela entrega. Por em QUAL marco uma task vai, isso ela
    faz, como faz com `bloco`.
    """
    chamador.exigir("gerir_marcos")
    return await repo.criar(session, projeto.id, body.nome, body.data_alvo)


@rotas.get("/marcos/{marco_id}", response_model=MarcoComPrevisao)
async def ver_marco(
    marco_id: int,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("ler")
    marco = await repo.buscar(session, projeto.id, marco_id)
    if marco is None:
        raise HTTPException(404, f"marco {marco_id} nao encontrado")

    tasks = [
        TaskOut.model_validate(t).model_dump()
        for t in await repo.tasks_do_marco(session, projeto.id, marco_id)
    ]
    saida = MarcoComPrevisao.model_validate(marco, from_attributes=True)
    saida.previsao = dom_previsao.prever(
        {
            "nome": marco.nome,
            "data_alvo": marco.data_alvo,
            "fechado_em": marco.fechado_em,
        },
        tasks,
        await _calibracao_do_projeto(session, projeto.id),
    )
    return saida


@rotas.patch("/marcos/{marco_id}", response_model=MarcoOut)
async def editar_marco(
    marco_id: int,
    body: MarcoEdicao,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("gerir_marcos")
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")

    marco = await repo.editar(session, projeto.id, marco_id, campos)
    if marco is None:
        raise HTTPException(404, f"marco {marco_id} nao encontrado")
    return marco


@rotas.patch("/marcos/{marco_id}/fechamento", response_model=MarcoOut)
async def fechar_marco(
    marco_id: int,
    body: FechamentoMarco,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Fecha ou reabre o marco. Reabrir nao perde nada: so limpa a data."""
    chamador.exigir("gerir_marcos")
    marco = await repo.fechar(session, projeto.id, marco_id, body.fechado)
    if marco is None:
        raise HTTPException(404, f"marco {marco_id} nao encontrado")
    return marco


@rotas.delete("/marcos/{marco_id}", status_code=204)
async def apagar_marco(
    marco_id: int,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Apaga o marco. As tasks dele NAO sao apagadas.

    A FK e SET NULL: elas so perdem o agrupamento. Apagar um marco nunca
    pode apagar trabalho -- e o tipo de perda que ninguem espera de
    "remover a etiqueta".
    """
    chamador.exigir("gerir_marcos")
    if not await repo.apagar(session, projeto.id, marco_id):
        raise HTTPException(404, f"marco {marco_id} nao encontrado")
    return Response(status_code=204)
