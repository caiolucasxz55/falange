"""Escrita e leitura da linha do tempo.

`registrar` NAO commita, de proposito: ele entra na transacao de quem
chamou. Ou a mudanca e o evento dela acontecem juntos, ou nenhum dos dois
acontece -- um evento commitado a parte poderia sobreviver a um rollback e
descrever algo que nunca foi.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Evento, TipoEvento
from backend.seguranca.contexto import autor_atual


async def registrar(
    session: AsyncSession,
    projeto_id: int,
    tipo: TipoEvento,
    task_id: Optional[int] = None,
    dados: Optional[dict[str, Any]] = None,
    autor_id: Optional[int] = None,
) -> None:
    """Anota que algo aconteceu. Nao commita.

    `autor_id` vem do contexto do request quando nao e passado. Passar
    explicitamente serve para teste e para o caso raro de registrar em
    nome de outra pessoa.
    """
    session.add(
        Evento(
            projeto_id=projeto_id,
            tipo=tipo,
            task_id=task_id,
            autor_id=autor_id if autor_id is not None else autor_atual(),
            dados=dados or {},
        )
    )


async def listar(
    session: AsyncSession,
    projeto_id: int,
    desde: Optional[datetime] = None,
    limite: Optional[int] = None,
) -> list[Evento]:
    """Eventos do projeto, do mais recente para o mais antigo."""
    q = select(Evento).where(Evento.projeto_id == projeto_id)
    if desde is not None:
        q = q.where(Evento.criado_em >= desde)
    q = q.order_by(Evento.criado_em.desc(), Evento.id.desc())
    if limite:
        q = q.limit(limite)
    return list((await session.scalars(q)).all())


async def desde_dias(
    session: AsyncSession, projeto_id: int, dias: int, limite: Optional[int] = None
) -> list[Evento]:
    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    return await listar(session, projeto_id, desde=corte, limite=limite)


async def contar(session: AsyncSession, projeto_id: int) -> int:
    """Quantos eventos o projeto tem.

    Serve para `/evolucao` poder dizer "ainda nao ha historico suficiente"
    em vez de desenhar um grafico de quase nada e parecer que o time nao
    fez nada.
    """
    from sqlalchemy import func

    q = select(func.count(Evento.id)).where(Evento.projeto_id == projeto_id)
    return int((await session.scalar(q)) or 0)
