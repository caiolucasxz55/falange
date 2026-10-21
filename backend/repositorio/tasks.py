"""Consultas e escritas da task."""

from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dominio.perfil import CAMPOS_AJUSTAVEIS, deve_registrar_ajuste
from backend.models import (
    ABERTAS,
    Bloco,
    Decisao,
    Prioridade,
    Status,
    Task,
    TipoDecisao,
)
from backend.repositorio import criterios as criterios_repo
from backend.repositorio import usuarios
from backend.repositorio.aprendizado import rebaixar_se_preciso

# CASE explicito: a ordem do enum no Postgres nao e a ordem de prioridade.
_ORDEM_PRIORIDADE = case(
    (Task.prioridade == Prioridade.alta, 0),
    (Task.prioridade == Prioridade.media, 1),
    else_=2,
)


def _valor(bruto):
    """Enum vira texto: JSONB nao guarda Enum do SQLAlchemy."""
    return getattr(bruto, "value", bruto)


async def _ligar_responsavel(session: AsyncSession, dados: dict) -> dict:
    """Resolve o texto `responsavel` para `responsavel_id`, quando der.

    Mora aqui, e nao na rota, para valer igual pela tela e pelo MCP -- e
    porque manter a FK em sincronia com o texto e um assunto de dados, nao
    de HTTP. Mesma regra do backfill da migration 0007: liga quem casa por
    nome, e deixa NULL para nome solto. Sem isto a coluna ficava sempre
    NULL, apesar de aparecer na API como "o id e o fato".
    """
    if "responsavel" not in dados:
        return dados
    pessoa = await usuarios.buscar_por_nome(session, dados["responsavel"] or "")
    return {**dados, "responsavel_id": pessoa.id if pessoa else None}


async def criar(
    session: AsyncSession, dados: dict, criterios: Optional[list[str]] = None
) -> Task:
    """Cria a task e, no MESMO commit, os criterios de aceite dela.

    Os criterios entram por aqui, e nao numa chamada separada da rota, para
    nao existir o estado intermediario de uma task sem o checklist que ela
    declarou ter: ou nasce com os criterios, ou nao nasce.
    """
    task = Task(**await _ligar_responsavel(session, dados))
    session.add(task)
    # Flush em vez de commit: precisa do id para a FK do criterio, mas ainda
    # dentro da mesma transacao.
    await session.flush()
    await criterios_repo.criar_para(session, task.id, criterios or [])
    await session.commit()
    await session.refresh(task)
    return task


async def buscar(
    session: AsyncSession, projeto_id: int, task_id: int
) -> Optional[Task]:
    """None tambem quando a task existe em OUTRO projeto.

    De proposito: para quem pergunta de fora do projeto, ela nao
    existe. Devolver a task e deixar a rota decidir vazaria o titulo
    de um projeto para outro.
    """
    task = await session.get(Task, task_id)
    return task if task is not None and task.projeto_id == projeto_id else None


async def existe_em_outro_projeto(
    session: AsyncSession, projeto_id: int, task_id: int
) -> bool:
    """A task existe, mas pertence a outro projeto?

    Serve para a rota separar "nao existe" (404) de "existe, mas e de outro
    projeto" (409). Nao devolve a task nem o projeto dela: so o suficiente
    para a mensagem, sem vazar titulo de um projeto para outro.
    """
    task = await session.get(Task, task_id)
    return task is not None and task.projeto_id != projeto_id


async def listar(
    session: AsyncSession,
    projeto_id: int,
    bloco: Optional[Bloco] = None,
    status: Optional[Status] = None,
    responsavel: Optional[str] = None,
    prioridade: Optional[Prioridade] = None,
) -> list[Task]:
    q = (
        select(Task)
        .where(Task.projeto_id == projeto_id)
        .order_by(_ORDEM_PRIORIDADE, Task.id)
    )
    if bloco is not None:
        q = q.where(Task.bloco == bloco)
    if status is not None:
        q = q.where(Task.status == status)
    if responsavel is not None:
        q = q.where(Task.responsavel == responsavel)
    if prioridade is not None:
        q = q.where(Task.prioridade == prioridade)
    return list((await session.scalars(q)).all())


async def definir_status(
    session: AsyncSession, projeto_id: int, task_id: int, status: Status
) -> Optional[Task]:
    task = await buscar(session, projeto_id, task_id)
    if task is None:
        return None
    task.status = status
    task.atualizada_em = func.now()

    # Primeira ida para em_andamento marca o inicio; depois nao sobrescreve.
    if status is Status.em_andamento and task.iniciada_em is None:
        task.iniciada_em = func.now()

    # Concluir nao precisa mais mexer em bloqueio nenhum: "bloqueada" e
    # DERIVADA de ter dependencia nao concluida (ver `dominio/grafo.py`).
    # Antes era preciso limpar o proprio bloqueio e o de quem esperava, e
    # esquecer isso em algum caminho deixava task travada por algo que ja
    # tinha acabado. Agora nao ha estado para desatualizar.
    if status is Status.concluida:
        task.concluida_em = func.now()
    else:
        # Reabrir (aberta ou em_andamento) desfaz a conclusao -- e volta a
        # travar quem dependia dela, sem precisar de nenhuma escrita.
        task.concluida_em = None

    await session.commit()
    await session.refresh(task)
    return task


async def contagem_global(session: AsyncSession) -> dict:
    """Contagem de TODOS os projetos, para o healthcheck.

    O `/health` responde antes de qualquer autenticacao e nao recebe
    projeto; escopar no `padrao` faria o numero mentir assim que existisse
    um segundo projeto.
    """
    q = select(Task.bloco, func.count(Task.id)).group_by(Task.bloco)
    bruto = {bloco.value: n for bloco, n in (await session.execute(q)).all()}
    por_bloco = {b.value: bruto.get(b.value, 0) for b in Bloco}
    return {"total": sum(por_bloco.values()), "por_bloco": por_bloco}


async def contagem_por_bloco(session: AsyncSession, projeto_id: int) -> dict:
    q = (
        select(Task.bloco, func.count(Task.id))
        .where(Task.projeto_id == projeto_id)
        .group_by(Task.bloco)
    )
    bruto = {bloco.value: n for bloco, n in (await session.execute(q)).all()}
    por_bloco = {b.value: bruto.get(b.value, 0) for b in Bloco}
    return {"total": sum(por_bloco.values()), "por_bloco": por_bloco}


async def contar_abertas(
    session: AsyncSession,
    projeto_id: int,
    bloco: Optional[Bloco] = None,
    responsavel: Optional[str] = None,
) -> int:
    q = select(func.count(Task.id)).where(
        Task.status.in_(ABERTAS), Task.projeto_id == projeto_id
    )
    if bloco is not None:
        q = q.where(Task.bloco == bloco)
    if responsavel is not None:
        q = q.where(Task.responsavel == responsavel)
    return int((await session.execute(q)).scalar_one())


async def editar(
    session: AsyncSession,
    projeto_id: int,
    task_id: int,
    campos: dict,
    fonte: Optional[str] = None,
) -> Optional[Task]:
    """Altera apenas os campos presentes em `campos`.

    `fonte` vem do header X-Falange-Fonte. Quando um humano (sem o header)
    corrige um campo de julgamento de uma task escrita pela IA, a correcao
    vira uma `decisao` do tipo ajuste_humano. Ninguem precisa anotar nada:
    e assim que o Falange aprende com o que o time desfaz.
    """
    task = await buscar(session, projeto_id, task_id)
    if task is None:
        return None

    antes = {
        campo: _valor(getattr(task, campo))
        for campo in CAMPOS_AJUSTAVEIS
        if campo in campos
    }

    # Trocar o texto do responsavel reaponta a FK no mesmo commit, senao
    # as duas colunas passariam a discordar.
    campos = await _ligar_responsavel(session, campos)

    for campo, valor in campos.items():
        setattr(task, campo, valor)
    task.atualizada_em = func.now()

    if deve_registrar_ajuste(task.origem, fonte, campos):
        depois = {campo: _valor(getattr(task, campo)) for campo in antes}
        alterados = {c: v for c, v in depois.items() if v != antes[c]}
        if alterados:
            registro = {
                "projeto_id": projeto_id,
                "tipo": TipoDecisao.ajuste_humano,
                "sugerido": {c: antes[c] for c in alterados},
                "escolhido": alterados,
                # O humano desfez a escolha da IA: nao foi aceita.
                "aceita": False,
                "task_id": task_id,
            }
            session.add(Decisao(**registro))
            await rebaixar_se_preciso(session, projeto_id, registro)

    await session.commit()
    await session.refresh(task)
    return task


async def remover(session: AsyncSession, projeto_id: int, task_id: int) -> bool:
    """Remove a task. As arestas de dependencia somem junto (CASCADE nos
    dois lados), entao nao sobra aresta apontando para id morto."""
    task = await buscar(session, projeto_id, task_id)
    if task is None:
        return False
    await session.delete(task)
    await session.commit()
    return True
