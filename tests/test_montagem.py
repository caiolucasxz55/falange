"""Montagem da resposta de task: o que o banco guarda + o que se deriva.

Nao tocam no banco. O que estes testes prendem e o CONTRATO -- que
`montar_task` preencha todo campo derivado e que a ordem dos criterios seja
a da coluna `ordem`, nao a do id.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from backend.models.enums import Bloco, Estimativa, Origem, Prioridade, Status
from backend.rotas.montagem import montar_task, montar_tasks
from backend.schemas.task import TaskNova

AGORA = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)


def task_falsa(task_id: int):
    """Uma task com a cara do model, sem precisar de sessao."""
    return SimpleNamespace(
        id=task_id,
        titulo=f"Task {task_id}",
        descricao="",
        estimativa=Estimativa.P,
        bloco=Bloco.backend,
        responsavel=None,
        responsavel_id=None,
        autor_id=None,
        status=Status.aberta,
        prioridade=Prioridade.media,
        criada_em=AGORA,
        atualizada_em=AGORA,
        iniciada_em=None,
        concluida_em=None,
        origem=Origem.humano,
    )


def criterio_falso(criterio_id: int, texto: str, ordem: int, cumprido=None):
    return SimpleNamespace(
        id=criterio_id,
        task_id=1,
        texto=texto,
        ordem=ordem,
        cumprido_em=cumprido,
        criado_em=AGORA,
    )


def test_monta_criterios_junto_dos_campos_do_grafo():
    saida = montar_task(
        task_falsa(1),
        arestas=[(1, 2)],
        concluidas=set(),
        criterios={1: [criterio_falso(9, "retorna 401 no token vencido", 0)]},
    )
    assert saida.depende_de == [2]
    assert saida.bloqueada is True
    assert [c.texto for c in saida.criterios] == ["retorna 401 no token vencido"]
    assert saida.criterios[0].cumprido_em is None


def test_ordem_e_a_da_coluna_ordem_nao_a_do_id():
    """O repositorio ordena por `ordem`; a montagem nao deve reordenar.

    Ids fora de ordem de proposito: se a montagem resolvesse ordenar por
    id, este teste quebraria -- que e o ponto.
    """
    criterios = {
        1: [
            criterio_falso(99, "primeiro", 0),
            criterio_falso(7, "segundo", 1),
        ]
    }
    saida = montar_task(task_falsa(1), [], set(), criterios)
    assert [c.texto for c in saida.criterios] == ["primeiro", "segundo"]


def test_task_sem_criterio_sai_com_lista_vazia_nao_com_erro():
    # As tasks antigas, em que a migration 0010 nao achou a linha.
    assert montar_task(task_falsa(1), [], set(), {}).criterios == []
    assert montar_task(task_falsa(1), [], set(), None).criterios == []


def test_montar_varias_nao_mistura_criterio_entre_tasks():
    saida = montar_tasks(
        [task_falsa(1), task_falsa(2)],
        arestas=[],
        concluidas=set(),
        criterios={1: [criterio_falso(1, "so da task 1", 0)]},
    )
    assert [c.texto for c in saida[0].criterios] == ["so da task 1"]
    assert saida[1].criterios == []


def test_criterio_cumprido_sai_com_a_data():
    saida = montar_task(
        task_falsa(1),
        [],
        set(),
        {1: [criterio_falso(1, "retorna 409 no ciclo", 0, cumprido=AGORA)]},
    )
    assert saida.criterios[0].cumprido_em == AGORA


# ---------------------------------------------------------------- TaskNova


def _nova(**campos):
    base = {"titulo": "Fazer a coisa", "estimativa": "P", "bloco": "backend"}
    return TaskNova(**{**base, **campos})


def test_criterios_sao_aparados_e_vazios_descartados():
    nova = _nova(criterios=["  retorna 401 no vencido  ", "   ", ""])
    assert nova.criterios == ["retorna 401 no vencido"]


def test_criterio_de_espacos_nao_passa_pelo_minimo():
    """Aparar ANTES de medir: 15 espacos tem 15 chars, e nenhum serve."""
    assert _nova(criterios=["               "]).criterios == []


def test_recusa_criterio_curto_ou_longo():
    with pytest.raises(ValueError):
        _nova(criterios=["curto"])
    with pytest.raises(ValueError):
        _nova(criterios=["x" * 201])


def test_recusa_mais_de_cinco_criterios():
    with pytest.raises(ValueError):
        _nova(criterios=["retorna 401 aqui"] * 6)


def test_lista_vazia_e_aceita_por_compatibilidade():
    """A tela ainda nao manda criterio; exigir aqui a derrubaria."""
    assert _nova().criterios == []
