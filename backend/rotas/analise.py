"""Rotas de leitura analitica: priorizacao e calibracao.

So leem. A conta mora em `dominio/`; aqui a rota so busca no banco, chama a
funcao pura e devolve.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db import get_session
from backend.dominio import evolucao as dom_evolucao
from backend.dominio import previsao as dom_previsao
from backend.dominio.calibracao import calibrar
from backend.dominio.priorizacao import ranquear
from backend.models import Bloco, Status
from backend.models import Projeto
from backend.repositorio import dependencias as repo_deps
from backend.repositorio import eventos as repo_eventos
from backend.repositorio import marcos as repo_marcos
from backend.repositorio import tasks as repo_tasks
from backend.schemas import TaskOut
from backend.schemas.texto import NomeOpcional
from backend.seguranca.dependencias import (
    Chamador,
    obter_chamador,
    obter_projeto,
)

rotas = APIRouter(tags=["analise"])


@rotas.get("/priorizacao")
async def priorizacao(
    responsavel: NomeOpcional = None,
    bloco: Optional[Bloco] = None,
    limite: int = Query(5, ge=1, le=50),
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Ranking explicado das tasks que dao para pegar agora.

    O ranking roda sobre TODAS as tasks: a cadeia de bloqueio e global, e
    filtrar antes quebraria a conta de quem destrava quem. O filtro de bloco
    se aplica depois, so nas sugestoes.
    """
    chamador.exigir("ler")
    tasks = [
        TaskOut.model_validate(t).model_dump()
        for t in await repo_tasks.listar(session, projeto.id)
    ]

    # Carga so de quem aparece como responsavel: alimenta o aviso de sobrecarga.
    cargas = {}
    for nome in {t["responsavel"] for t in tasks if t["responsavel"]}:
        abertas = await repo_tasks.contar_abertas(
            session, projeto.id, responsavel=nome
        )
        cargas[nome] = {
            "tasks_abertas": abertas,
            "limite": settings.limite_sobrecarga,
            "sobrecarregado": abertas > settings.limite_sobrecarga,
        }

    arestas = await repo_deps.listar_arestas(session, projeto.id)
    # Os marcos entram para o peso de prazo e para o alerta
    # `marco_em_risco`: e o que da dado real a "pre-requisito de uma
    # entrega proxima", que a regra de prioridade sempre prometeu.
    marcos = [
        {
            "id": m.id,
            "nome": m.nome,
            "data_alvo": m.data_alvo,
            "fechado_em": m.fechado_em,
        }
        for m in await repo_marcos.listar(session, projeto.id)
    ]
    saida = ranquear(
        tasks, datetime.now(timezone.utc), cargas, responsavel, arestas, marcos
    )

    if bloco is not None:
        saida["sugestoes"] = [s for s in saida["sugestoes"] if s["bloco"] == bloco.value]
    saida["sugestoes"] = saida["sugestoes"][:limite]
    return saida


@rotas.get("/calibracao")
async def calibracao(
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Compara a estimativa com a duracao real das tasks ja concluidas.

    So entram tasks com os dois marcos de tempo; o resto nao da para medir.
    """
    chamador.exigir("ler")
    concluidas = await repo_tasks.listar(
        session, projeto.id, status=Status.concluida
    )
    return calibrar([TaskOut.model_validate(t).model_dump() for t in concluidas])

@rotas.get("/evolucao")
async def evolucao(
    semanas: int = Query(8, ge=1, le=26),
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Como o time esta andando: throughput, tempo de ciclo e marcos.

    Sai dos EVENTOS, nao do estado atual -- as duas perguntas aqui sao
    sobre a passagem do tempo, e o estado atual nao a guarda. Por isso
    tudo o que aconteceu antes de a tabela de eventos existir nao aparece:
    `aviso` diz isso quando ha pouco registro, em vez de desenhar um
    grafico quase vazio que parece "o time parou".
    """
    chamador.exigir("ler")

    # A janela da busca cobre a grade inteira, com uma semana de folga
    # para o ciclo que comecou antes da primeira segunda aparecer.
    desde = datetime.now(timezone.utc) - timedelta(weeks=semanas + 1)
    linha_do_tempo = await repo_eventos.listar(session, projeto.id, desde=desde)

    tasks = {
        t.id: t for t in await repo_tasks.listar(session, projeto.id)
    }
    saida = dom_evolucao.montar(linha_do_tempo, tasks, quantas_semanas=semanas)

    # Os marcos entram com a previsao: "o time esta andando" e "a entrega
    # vai dar" sao a mesma pergunta vista de dois lados.
    marcos = await repo_marcos.listar(session, projeto.id, incluir_fechados=False)
    por_marco = await repo_marcos.tasks_por_marco(session, projeto.id)
    calibracao_atual = calibrar(
        [
            TaskOut.model_validate(t).model_dump()
            for t in tasks.values()
            if t.status == Status.concluida
        ]
    )
    saida["marcos"] = [
        {
            "id": m.id,
            "nome": m.nome,
            **dom_previsao.prever(
                {"nome": m.nome, "data_alvo": m.data_alvo, "fechado_em": m.fechado_em},
                [
                    TaskOut.model_validate(t).model_dump()
                    for t in por_marco.get(m.id, [])
                ],
                calibracao_atual,
            ),
        }
        for m in marcos
    ]
    return saida
