"""Rotas de leitura analitica: priorizacao e calibracao.

So leem. A conta mora em `dominio/`; aqui a rota so busca no banco, chama a
funcao pura e devolve.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db import get_session
from backend.dominio.calibracao import calibrar
from backend.dominio.priorizacao import ranquear
from backend.models import Bloco, Status
from backend.repositorio import tasks as repo_tasks
from backend.schemas import TaskOut
from backend.seguranca.dependencias import Chamador, obter_chamador

rotas = APIRouter(tags=["analise"])


@rotas.get("/priorizacao")
async def priorizacao(
    responsavel: Optional[str] = None,
    bloco: Optional[Bloco] = None,
    limite: int = Query(5, ge=1, le=50),
    chamador: Chamador = Depends(obter_chamador),
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
        for t in await repo_tasks.listar(session)
    ]

    # Carga so de quem aparece como responsavel: alimenta o aviso de sobrecarga.
    cargas = {}
    for nome in {t["responsavel"] for t in tasks if t["responsavel"]}:
        abertas = await repo_tasks.contar_abertas(session, responsavel=nome)
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


@rotas.get("/calibracao")
async def calibracao(
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    """Compara a estimativa com a duracao real das tasks ja concluidas.

    So entram tasks com os dois marcos de tempo; o resto nao da para medir.
    """
    chamador.exigir("ler")
    concluidas = await repo_tasks.listar(session, status=Status.concluida)
    return calibrar([TaskOut.model_validate(t).model_dump() for t in concluidas])
