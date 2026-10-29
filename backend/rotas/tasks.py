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
from backend.dominio import conclusao, grafo
from backend.dominio.papeis import acoes_para_campos
from backend.models import Bloco, Origem, Prioridade, Status
from backend.models import Projeto
from backend.repositorio import criterios as repo_criterios
from backend.repositorio import dependencias as repo_deps
from backend.repositorio import evidencias as repo_evidencias
from backend.repositorio import tasks as repo
from backend.rotas.montagem import montar_task, montar_tasks
from backend.seguranca.dependencias import (
    Chamador,
    obter_chamador,
    obter_projeto,
)
from backend.schemas.texto import NomeOpcional
from backend.schemas import (
    DependenciaNova,
    EvidenciaNova,
    EvidenciaOut,
    Carga,
    MudancaStatus,
    TaskEdicao,
    TaskNova,
    TaskOut,
)

rotas = APIRouter(tags=["tasks"])


async def _montar_uma(
    session: AsyncSession, projeto_id: int, task
) -> TaskOut:
    """Monta UMA task com tudo o que ela deriva.

    Existe porque seis rotas devolvem uma task so, e cada uma repetia as
    mesmas buscas. Uma esquecer um campo era questao de tempo -- e foi assim
    que `criterios` entrou em cinco rotas de uma vez.
    """
    return montar_task(
        task,
        await repo_deps.listar_arestas(session, projeto_id),
        await repo_deps.concluidas(session, projeto_id),
        await repo_criterios.por_task(session, [task.id]),
    )


@rotas.post("/tasks", response_model=TaskOut, status_code=201)
async def criar_task(
    nova: TaskNova,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
    x_falange_fonte: Optional[str] = Header(default=None),
):
    chamador.exigir("criar_task")
    dados = nova.model_dump()
    for acao in sorted(acoes_para_campos(dados, chamador.nome)):
        chamador.exigir(acao)

    # Quem escreveu a task sai do header, nao do corpo: autoria declarada
    # pelo cliente seria forjavel e envenenaria calibracao e perfil.
    dados["origem"] = Origem.ia if x_falange_fonte == "mcp" else Origem.humano
    # Agora da para dizer QUEM, e nao so se foi IA ou humano.
    dados["autor_id"] = chamador.id
    dados["projeto_id"] = projeto.id
    # `criterios` nao e coluna da task: sai do dict antes de virar Task(**).
    criterios = dados.pop("criterios", [])
    task = await repo.criar(session, dados, criterios)
    # Task nova nao tem aresta, mas a saida passa pela mesma montagem:
    # um caminho so para o contrato nao divergir entre rotas.
    return montar_task(
        task, [], set(), await repo_criterios.por_task(session, [task.id])
    )


@rotas.get("/tasks", response_model=list[TaskOut])
async def listar_tasks(
    bloco: Optional[Bloco] = None,
    status: Optional[Status] = None,
    # Aparado como na gravacao: filtro com espaco sobrando achava zero.
    responsavel: NomeOpcional = None,
    prioridade: Optional[Prioridade] = None,
    bloqueada: Optional[bool] = None,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("ler")
    tasks = await repo.listar(
        session,
        projeto.id,
        bloco=bloco,
        status=status,
        responsavel=responsavel,
        prioridade=prioridade,
    )
    # O grafo do projeto inteiro, uma vez: `travando` e `bloqueada`
    # dependem de arestas que podem sair de tasks fora do filtro.
    arestas = await repo_deps.listar_arestas(session, projeto.id)
    concluidas = await repo_deps.concluidas(session, projeto.id)
    # Uma consulta para a lista inteira: por task seria N+1 no board.
    criterios = await repo_criterios.por_task(session, [t.id for t in tasks])
    saida = montar_tasks(tasks, arestas, concluidas, criterios)

    # Este filtro e o unico que nao desce para o SQL: `bloqueada` nao e
    # coluna, e a resposta so existe depois da montagem.
    if bloqueada is not None:
        saida = [s for s in saida if s.bloqueada is bloqueada]
    return saida


@rotas.get("/tasks/contagem-por-bloco")
async def contar_tasks_por_bloco(
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("ler")
    return await repo.contagem_por_bloco(session, projeto.id)


@rotas.get("/carga", response_model=Carga)
async def carga(
    bloco: Optional[Bloco] = None,
    responsavel: NomeOpcional = None,
    limite: Optional[int] = Query(None, description="default: LIMITE_SOBRECARGA do .env"),
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Quantas tasks abertas um bloco ou uma pessoa carrega, e se passou do limite."""
    chamador.exigir("ler")
    if bloco is None and responsavel is None:
        raise HTTPException(400, "informe bloco ou responsavel")

    teto = limite if limite is not None else settings.limite_sobrecarga
    abertas = await repo.contar_abertas(
        session, projeto.id, bloco=bloco, responsavel=responsavel
    )
    return Carga(
        escopo="responsavel" if responsavel else "bloco",
        alvo=responsavel or (bloco.value if bloco else None),
        tasks_abertas=abertas,
        limite=teto,
        sobrecarregado=abertas > teto,
    )


@rotas.get("/tasks/{task_id}", response_model=TaskOut)
async def buscar_task(
    task_id: int,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("ler")
    task = await repo.buscar(session, projeto.id, task_id)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return await _montar_uma(session, projeto.id, task)


@rotas.post(
    "/tasks/{task_id}/dependencias", response_model=TaskOut, status_code=201
)
async def adicionar_dependencia(
    task_id: int,
    body: DependenciaNova,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Faz esta task esperar por outra.

    Recusa auto-dependencia, ciclo e cruzar projeto. A deteccao de ciclo
    roda sobre o grafo inteiro: com N:N, a volta pode fechar por um caminho
    de varios passos.
    """
    chamador.exigir("marcar_bloqueio")

    task = await repo.buscar(session, projeto.id, task_id)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")

    alvo = body.depende_de
    if alvo == task_id:
        raise HTTPException(409, "uma task nao pode depender de si mesma")

    if await repo.buscar(session, projeto.id, alvo) is None:
        if await repo.existe_em_outro_projeto(session, projeto.id, alvo):
            raise HTTPException(409, f"task {alvo} e de outro projeto")
        raise HTTPException(404, f"task {alvo} nao encontrada")

    arestas = await repo_deps.listar_arestas(session, projeto.id)
    if grafo.criaria_ciclo(arestas, task_id, alvo):
        raise HTTPException(
            409,
            f"fazer {task_id} depender de {alvo} criaria um ciclo de dependencia",
        )

    await repo_deps.adicionar(session, task_id, alvo)
    return await _montar_uma(session, projeto.id, task)


@rotas.delete(
    "/tasks/{task_id}/dependencias/{depende_de_id}", response_model=TaskOut
)
async def remover_dependencia(
    task_id: int,
    depende_de_id: int,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Solta esta task da outra."""
    chamador.exigir("marcar_bloqueio")

    task = await repo.buscar(session, projeto.id, task_id)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")

    if not await repo_deps.remover(session, task_id, depende_de_id):
        raise HTTPException(
            404, f"task {task_id} nao depende de {depende_de_id}"
        )
    return await _montar_uma(session, projeto.id, task)


@rotas.patch("/tasks/{task_id}/status", response_model=TaskOut)
async def mudar_status(
    task_id: int,
    body: MudancaStatus,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("mudar_status_task")

    # Concluir e a unica transicao com porteiro: a IA precisa de prova em
    # todos os criterios. As outras nao afirmam nada sobre o trabalho estar
    # pronto, entao nao ha o que provar.
    if body.status == Status.concluida:
        task = await repo.buscar(session, projeto.id, task_id)
        if task is None:
            raise HTTPException(404, f"task {task_id} nao encontrada")

        criterios = (
            await repo_criterios.por_task(session, [task_id])
        ).get(task_id, [])
        # O papel vem do banco a cada request (ver seguranca/dependencias):
        # rebaixar alguem vale no request seguinte, nao no vencimento do
        # token. Aqui isso importa -- e a decisao mais sensivel da API.
        pode, motivo = conclusao.pode_concluir(chamador.papel, criterios)
        if not pode:
            # 409, nao 403: o papel ALCANCA a acao; o que falta e a prova.
            # 403 mandaria a IA pedir permissao a um humano, quando o
            # caminho certo e registrar a evidencia.
            raise HTTPException(409, motivo)

    task = await repo.definir_status(session, projeto.id, task_id, body.status)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return await _montar_uma(session, projeto.id, task)


# --------------------------------------------------------------- evidencia


@rotas.get("/tasks/{task_id}/evidencias", response_model=list[EvidenciaOut])
async def listar_evidencias(
    task_id: int,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """As provas anexadas a esta task."""
    chamador.exigir("ler")
    if await repo.buscar(session, projeto.id, task_id) is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return await repo_evidencias.listar_por_task(session, task_id)


@rotas.post(
    "/tasks/{task_id}/evidencias", response_model=EvidenciaOut, status_code=201
)
async def registrar_evidencia(
    task_id: int,
    body: EvidenciaNova,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Anexa uma prova e liga os criterios que ela cumpre."""
    chamador.exigir("registrar_evidencia")
    if await repo.buscar(session, projeto.id, task_id) is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")

    evidencia, erro = await repo_evidencias.registrar(
        session,
        task_id,
        body.tipo,
        body.referencia,
        body.resumo,
        chamador.id,
        body.criterio_ids,
    )
    if erro:
        # 409: o pedido e coerente, mas cruza a fronteira de outra task --
        # a mesma semantica das dependencias entre projetos.
        raise HTTPException(409, erro)
    return evidencia


@rotas.delete(
    "/tasks/{task_id}/evidencias/{evidencia_id}", status_code=204
)
async def apagar_evidencia(
    task_id: int,
    evidencia_id: int,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    """Tira a prova. Os criterios dela voltam a "nao verificado".

    Destrutiva, entao exige a permissao ampla -- nao ha
    `apagar_evidencia_propria`: a IA registra a propria prova, e deixar que
    ela tambem a apagasse daria a ela como desfazer o rastro do que fez.
    """
    chamador.exigir("apagar_task")
    if await repo.buscar(session, projeto.id, task_id) is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")

    if not await repo_evidencias.remover(session, task_id, evidencia_id):
        raise HTTPException(
            404, f"evidencia {evidencia_id} nao e da task {task_id}"
        )
    return Response(status_code=204)


@rotas.patch("/tasks/{task_id}", response_model=TaskOut)
async def editar_task(
    task_id: int,
    body: TaskEdicao,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
    # O MCP se identifica; a tela nao manda nada. E assim que o backend
    # sabe se quem corrigiu a task foi a IA ou um humano.
    x_falange_fonte: Optional[str] = Header(default=None),
):
    chamador.exigir("editar_task")
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")

    # Carrega ANTES de decidir a permissao: o que importa e o que esta
    # mudando, nao que campos vieram no corpo. O formulario da tela reenvia
    # a task inteira, entao julgar por presenca cobraria `definir_prioridade`
    # de quem so corrigiu o titulo.
    atual = await repo.buscar(session, projeto.id, task_id)
    if atual is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    atuais = {"prioridade": atual.prioridade, "responsavel": atual.responsavel}
    for acao in sorted(acoes_para_campos(campos, chamador.nome, atuais)):
        chamador.exigir(acao)

    task = await repo.editar(
        session, projeto.id, task_id, campos, fonte=x_falange_fonte
    )
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    return await _montar_uma(session, projeto.id, task)


# response_class=Response: um 204 nao pode ter corpo, e sem isso o FastAPI
# ainda manda content-type: application/json, o que faz o navegador abortar.
@rotas.delete("/tasks/{task_id}", status_code=204, response_class=Response)
async def apagar_task(
    task_id: int,
    chamador: Chamador = Depends(obter_chamador),
    projeto: Projeto = Depends(obter_projeto),
    session: AsyncSession = Depends(get_session),
):
    # Precisa carregar antes de decidir: quem so apaga o proprio precisa do
    # autor para ser comparado.
    task = await repo.buscar(session, projeto.id, task_id)
    if task is None:
        raise HTTPException(404, f"task {task_id} nao encontrada")
    chamador.exigir_propria("apagar_task", task.autor_id)

    if not await repo.remover(session, projeto.id, task_id):
        raise HTTPException(404, f"task {task_id} nao encontrada")
