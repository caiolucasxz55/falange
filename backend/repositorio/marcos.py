"""Consultas e escritas do marco.

Como no resto do pacote: nao levanta `HTTPException`. Devolve `None`,
`False` ou `(valor, erro)` e deixa a rota traduzir para HTTP.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Marco, Task


async def listar(
    session: AsyncSession, projeto_id: int, incluir_fechados: bool = True
) -> list[Marco]:
    q = select(Marco).where(Marco.projeto_id == projeto_id)
    if not incluir_fechados:
        q = q.where(Marco.fechado_em.is_(None))
    # Por data, com os sem data no fim: o que tem prazo e o que a pessoa
    # esta procurando. NULLS LAST explicito -- no Postgres, ASC poe NULL
    # por ultimo, mas depender disso e depender do dialeto.
    return list(
        (
            await session.scalars(
                q.order_by(Marco.data_alvo.asc().nullslast(), Marco.id)
            )
        ).all()
    )


async def buscar(
    session: AsyncSession, projeto_id: int, marco_id: int
) -> Optional[Marco]:
    """None tambem quando o marco existe em OUTRO projeto.

    Mesma semantica da task: para quem pergunta de fora, marco de outro
    projeto nao existe.
    """
    marco = await session.get(Marco, marco_id)
    if marco is None or marco.projeto_id != projeto_id:
        return None
    return marco


async def criar(
    session: AsyncSession, projeto_id: int, nome: str, data_alvo=None
) -> Marco:
    marco = Marco(projeto_id=projeto_id, nome=nome, data_alvo=data_alvo)
    session.add(marco)
    await session.commit()
    await session.refresh(marco)
    return marco


async def editar(
    session: AsyncSession, projeto_id: int, marco_id: int, campos: dict
) -> Optional[Marco]:
    marco = await buscar(session, projeto_id, marco_id)
    if marco is None:
        return None
    for campo, valor in campos.items():
        setattr(marco, campo, valor)
    await session.commit()
    await session.refresh(marco)
    return marco


async def fechar(
    session: AsyncSession, projeto_id: int, marco_id: int, fechado: bool
) -> Optional[Marco]:
    """Fecha ou reabre. Reabrir e so limpar a data: nao ha estado perdido."""
    marco = await buscar(session, projeto_id, marco_id)
    if marco is None:
        return None
    marco.fechado_em = datetime.now(timezone.utc) if fechado else None
    await session.commit()
    await session.refresh(marco)
    return marco


async def apagar(
    session: AsyncSession, projeto_id: int, marco_id: int
) -> bool:
    """Apaga o marco. As tasks dele NAO sao apagadas.

    A FK e SET NULL, entao elas so perdem o agrupamento. Apagar um marco
    nunca pode apagar trabalho -- e o tipo de perda que ninguem espera de
    "remover a etiqueta".
    """
    marco = await buscar(session, projeto_id, marco_id)
    if marco is None:
        return False
    await session.delete(marco)
    await session.commit()
    return True


async def tasks_do_marco(
    session: AsyncSession, projeto_id: int, marco_id: int
) -> list[Task]:
    q = select(Task).where(
        Task.projeto_id == projeto_id, Task.marco_id == marco_id
    )
    return list((await session.scalars(q)).all())


async def tasks_por_marco(
    session: AsyncSession, projeto_id: int
) -> dict[int, list[Task]]:
    """As tasks de TODOS os marcos do projeto, agrupadas. Uma consulta.

    A previsao de cada marco precisa das tasks dele; buscar por marco seria
    N+1 na tela de evolucao, que mostra todos de uma vez.
    """
    q = select(Task).where(
        Task.projeto_id == projeto_id, Task.marco_id.is_not(None)
    )
    agrupadas: dict[int, list[Task]] = {}
    for task in (await session.scalars(q)).all():
        agrupadas.setdefault(task.marco_id, []).append(task)
    return agrupadas


async def desligar_tasks(
    session: AsyncSession, projeto_id: int, marco_id: int
) -> int:
    """Tira todas as tasks de um marco. Devolve quantas sairam."""
    resultado = await session.execute(
        update(Task)
        .where(Task.projeto_id == projeto_id, Task.marco_id == marco_id)
        .values(marco_id=None)
    )
    await session.commit()
    return resultado.rowcount or 0
