"""Consultas. Toda regra de banco mora aqui; main.py so faz HTTP."""

from typing import Optional

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    ABERTAS,
    Autonomia,
    Bloco,
    Configuracao,
    Decisao,
    Nota,
    Preferencia,
    Prioridade,
    Status,
    NivelAutonomia,
    Task,
    TipoAcao,
    TipoDecisao,
)
from backend.autonomia import ACOES, NIVEIS, acoes_a_rebaixar
from backend.perfil import CAMPOS_AJUSTAVEIS, deve_registrar_ajuste


# CASE explicito: a ordem do enum no Postgres nao e a ordem de prioridade.
_ORDEM_PRIORIDADE = case(
    (Task.prioridade == Prioridade.alta, 0),
    (Task.prioridade == Prioridade.media, 1),
    else_=2,
)


async def criar(session: AsyncSession, dados: dict) -> Task:
    task = Task(**dados)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def buscar(session: AsyncSession, task_id: int) -> Optional[Task]:
    return await session.get(Task, task_id)


async def listar(
    session: AsyncSession,
    bloco: Optional[Bloco] = None,
    status: Optional[Status] = None,
    responsavel: Optional[str] = None,
    prioridade: Optional[Prioridade] = None,
) -> list[Task]:
    q = select(Task).order_by(_ORDEM_PRIORIDADE, Task.id)
    if bloco is not None:
        q = q.where(Task.bloco == bloco)
    if status is not None:
        q = q.where(Task.status == status)
    if responsavel is not None:
        q = q.where(Task.responsavel == responsavel)
    if prioridade is not None:
        q = q.where(Task.prioridade == prioridade)
    return list((await session.scalars(q)).all())


async def _criaria_ciclo(session: AsyncSession, task_id: int, alvo_id: int) -> bool:
    """Anda a cadeia de bloqueio a partir de alvo_id procurando voltar em task_id."""
    visitados: set[int] = set()
    atual: Optional[int] = alvo_id
    while atual is not None:
        if atual == task_id:
            return True
        if atual in visitados:
            return False
        visitados.add(atual)
        t = await session.get(Task, atual)
        atual = t.bloqueada_por if t else None
    return False


async def definir_bloqueio(
    session: AsyncSession, task_id: int, bloqueada_por: Optional[int]
) -> tuple[Optional[Task], Optional[str]]:
    """Retorna (task, erro). Recusa auto-bloqueio e ciclos."""
    task = await session.get(Task, task_id)
    if task is None:
        return None, f"task {task_id} nao encontrada"

    if bloqueada_por is not None:
        if bloqueada_por == task_id:
            return None, "uma task nao pode bloquear a si mesma"
        if await session.get(Task, bloqueada_por) is None:
            return None, f"task bloqueadora {bloqueada_por} nao encontrada"
        if await _criaria_ciclo(session, task_id, bloqueada_por):
            return None, (
                f"bloquear {task_id} por {bloqueada_por} criaria um ciclo de dependencia"
            )

    task.bloqueada_por = bloqueada_por
    task.atualizada_em = func.now()
    await session.commit()
    await session.refresh(task)
    return task, None


async def definir_status(
    session: AsyncSession, task_id: int, status: Status
) -> Optional[Task]:
    task = await session.get(Task, task_id)
    if task is None:
        return None
    task.status = status
    task.atualizada_em = func.now()

    # Primeira ida para em_andamento marca o inicio; depois nao sobrescreve.
    if status is Status.em_andamento and task.iniciada_em is None:
        task.iniciada_em = func.now()

    # Task concluida nao fica pendurada em bloqueio: o fato deixou de valer.
    # E quem esperava por ela tambem e liberado, no mesmo commit.
    if status is Status.concluida:
        task.concluida_em = func.now()
        task.bloqueada_por = None
        await session.execute(
            update(Task)
            .where(Task.bloqueada_por == task_id)
            .values(bloqueada_por=None, atualizada_em=func.now())
        )
    else:
        # Reabrir (aberta ou em_andamento) desfaz a conclusao.
        task.concluida_em = None

    await session.commit()
    await session.refresh(task)
    return task


async def contagem_por_bloco(session: AsyncSession) -> dict:
    q = select(Task.bloco, func.count(Task.id)).group_by(Task.bloco)
    bruto = {bloco.value: n for bloco, n in (await session.execute(q)).all()}
    por_bloco = {b.value: bruto.get(b.value, 0) for b in Bloco}
    return {"total": sum(por_bloco.values()), "por_bloco": por_bloco}


async def contar_abertas(
    session: AsyncSession,
    bloco: Optional[Bloco] = None,
    responsavel: Optional[str] = None,
) -> int:
    q = select(func.count(Task.id)).where(Task.status.in_(ABERTAS))
    if bloco is not None:
        q = q.where(Task.bloco == bloco)
    if responsavel is not None:
        q = q.where(Task.responsavel == responsavel)
    return int((await session.execute(q)).scalar_one())


async def editar(
    session: AsyncSession, task_id: int, campos: dict, fonte: Optional[str] = None
) -> Optional[Task]:
    """Altera apenas os campos presentes em `campos`.

    `fonte` vem do header X-Falange-Fonte. Quando um humano (sem o header)
    corrige um campo de julgamento de uma task escrita pela IA, a correcao
    vira uma `decisao` do tipo ajuste_humano. Ninguem precisa anotar nada:
    e assim que o Falange aprende com o que o time desfaz.
    """
    task = await session.get(Task, task_id)
    if task is None:
        return None

    antes = {
        campo: _valor(getattr(task, campo))
        for campo in CAMPOS_AJUSTAVEIS
        if campo in campos
    }

    for campo, valor in campos.items():
        setattr(task, campo, valor)
    task.atualizada_em = func.now()

    if deve_registrar_ajuste(task.origem, fonte, campos):
        depois = {campo: _valor(getattr(task, campo)) for campo in antes}
        alterados = {c: v for c, v in depois.items() if v != antes[c]}
        if alterados:
            registro = {
                "tipo": TipoDecisao.ajuste_humano,
                "sugerido": {c: antes[c] for c in alterados},
                "escolhido": alterados,
                # O humano desfez a escolha da IA: nao foi aceita.
                "aceita": False,
                "task_id": task_id,
            }
            session.add(Decisao(**registro))
            await _rebaixar_se_preciso(session, registro)

    await session.commit()
    await session.refresh(task)
    return task


async def remover(session: AsyncSession, task_id: int) -> bool:
    """Remove a task. Quem dependia dela fica com bloqueada_por = NULL
    (ON DELETE SET NULL), entao ninguem sobra apontando para um id morto."""
    task = await session.get(Task, task_id)
    if task is None:
        return False
    await session.delete(task)
    await session.commit()
    return True


async def criar_nota(session: AsyncSession, dados: dict) -> Nota:
    nota = Nota(**dados)
    session.add(nota)
    await session.commit()
    await session.refresh(nota)
    return nota


async def listar_notas(
    session: AsyncSession,
    resolvida: Optional[bool] = None,
    task_id: Optional[int] = None,
) -> list[Nota]:
    """Mais recentes primeiro: nota nova e a que interessa."""
    q = select(Nota).order_by(Nota.criada_em.desc(), Nota.id.desc())
    if resolvida is not None:
        q = q.where(Nota.resolvida == resolvida)
    if task_id is not None:
        q = q.where(Nota.task_id == task_id)
    return list((await session.scalars(q)).all())


async def resolver_nota(session: AsyncSession, nota_id: int) -> Optional[Nota]:
    nota = await session.get(Nota, nota_id)
    if nota is None:
        return None
    nota.resolvida = True
    await session.commit()
    await session.refresh(nota)
    return nota


async def editar_nota(
    session: AsyncSession, nota_id: int, campos: dict
) -> Optional[Nota]:
    """Altera apenas os campos presentes em `campos`."""
    nota = await session.get(Nota, nota_id)
    if nota is None:
        return None
    for campo, valor in campos.items():
        setattr(nota, campo, valor)
    await session.commit()
    await session.refresh(nota)
    return nota


async def remover_nota(session: AsyncSession, nota_id: int) -> bool:
    nota = await session.get(Nota, nota_id)
    if nota is None:
        return False
    await session.delete(nota)
    await session.commit()
    return True


# Valores usados quando a chave ainda nao foi gravada.
PADROES_CONFIGURACAO = {"perguntas_ativas": "true"}


async def ler_configuracao(session: AsyncSession) -> dict[str, str]:
    """Configuracao completa, com os padroes preenchendo o que falta."""
    linhas = (await session.scalars(select(Configuracao))).all()
    gravadas = {c.chave: c.valor for c in linhas}
    return {**PADROES_CONFIGURACAO, **gravadas}


async def definir_configuracao(
    session: AsyncSession, chave: str, valor: str
) -> dict[str, str]:
    atual = await session.get(Configuracao, chave)
    if atual is None:
        session.add(Configuracao(chave=chave, valor=valor))
    else:
        atual.valor = valor
        atual.atualizada_em = func.now()
    await session.commit()
    return await ler_configuracao(session)


def _valor(bruto):
    """Enum vira texto: JSONB nao guarda Enum do SQLAlchemy."""
    return getattr(bruto, "value", bruto)


async def criar_decisao(session: AsyncSession, dados: dict) -> Decisao:
    decisao = Decisao(**dados)
    session.add(decisao)
    await _rebaixar_se_preciso(session, dados)
    await session.commit()
    await session.refresh(decisao)
    return decisao


async def _rebaixar_se_preciso(session: AsyncSession, decisao: dict) -> None:
    """Discordar de algo feito no automatico tira a autonomia na hora.

    Nao commita: entra no mesmo commit de quem registrou a decisao.
    """
    niveis = {
        linha.tipo_acao.value: linha.nivel.value
        for linha in (await session.scalars(select(Autonomia))).all()
    }
    for acao, novo in acoes_a_rebaixar(decisao, niveis).items():
        linha = await session.get(Autonomia, TipoAcao(acao))
        if linha is not None:
            linha.nivel = NivelAutonomia(novo)
            linha.atualizado_em = func.now()


async def listar_decisoes(
    session: AsyncSession, tipo: Optional[TipoDecisao] = None, limite: int = 500
) -> list[Decisao]:
    """Mais recentes primeiro: o habito de agora pesa mais que o de um ano."""
    q = select(Decisao).order_by(Decisao.criada_em.desc(), Decisao.id.desc())
    if tipo is not None:
        q = q.where(Decisao.tipo == tipo)
    return list((await session.scalars(q.limit(limite))).all())


async def criar_preferencia(session: AsyncSession, dados: dict) -> Preferencia:
    preferencia = Preferencia(**dados)
    session.add(preferencia)
    await session.commit()
    await session.refresh(preferencia)
    return preferencia


async def listar_preferencias(
    session: AsyncSession, ativa: Optional[bool] = None
) -> list[Preferencia]:
    q = select(Preferencia).order_by(Preferencia.id)
    if ativa is not None:
        q = q.where(Preferencia.ativa == ativa)
    return list((await session.scalars(q)).all())


async def definir_preferencia_ativa(
    session: AsyncSession, preferencia_id: int, ativa: bool
) -> Optional[Preferencia]:
    preferencia = await session.get(Preferencia, preferencia_id)
    if preferencia is None:
        return None
    preferencia.ativa = ativa
    await session.commit()
    await session.refresh(preferencia)
    return preferencia


async def ler_autonomia(session: AsyncSession) -> dict[str, str]:
    """Nivel de cada acao, com o padrao preenchendo o que nunca foi gravado."""
    linhas = (await session.scalars(select(Autonomia))).all()
    gravados = {linha.tipo_acao.value: linha.nivel.value for linha in linhas}
    return {acao: gravados.get(acao, NIVEIS[0]) for acao in ACOES}


async def definir_autonomia(
    session: AsyncSession, tipo_acao: TipoAcao, nivel: NivelAutonomia
) -> dict[str, str]:
    linha = await session.get(Autonomia, tipo_acao)
    if linha is None:
        session.add(Autonomia(tipo_acao=tipo_acao, nivel=nivel))
    else:
        linha.nivel = nivel
        linha.atualizado_em = func.now()
    await session.commit()
    return await ler_autonomia(session)
