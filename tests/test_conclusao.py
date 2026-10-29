"""Quem conclui o que, e sob que prova.

O modulo e puro, entao os testes nao precisam de banco. Vale a pena
escrever os dois lados: o que a IA NAO pode e o que o humano pode mesmo
assim.
"""

import pytest

from backend.dominio.conclusao import (
    concluida_sem_evidencia,
    criterios_sem_prova,
    pode_concluir,
)


def criterio(evidencia_id=None):
    return {"evidencia_id": evidencia_id}


class ComoLinhaDoBanco:
    """O dominio aceita dict ou objeto; a rota passa o model."""

    def __init__(self, evidencia_id=None):
        self.evidencia_id = evidencia_id


# -------------------------------------------------------------------- IA


def test_ia_conclui_com_prova_em_todos_os_criterios():
    pode, motivo = pode_concluir("ia", [criterio(1), criterio(2)])
    assert pode is True
    assert motivo == ""


def test_ia_nao_conclui_com_um_criterio_sem_prova():
    pode, motivo = pode_concluir("ia", [criterio(1), criterio(None)])
    assert pode is False
    assert "#2" in motivo
    assert "registrar_evidencia" in motivo


def test_ia_nao_conclui_task_sem_criterio_nenhum():
    """A brecha que fecharia a regra sozinha.

    "Todos os criterios com evidencia" e verdade por vacuidade numa lista
    vazia. Se isso passasse, a IA burlaria a exigencia de prova so criando
    a task sem criterio -- justamente ela, que escolhe os criterios.
    """
    pode, motivo = pode_concluir("ia", [])
    assert pode is False
    assert "sem criterio de aceite" in motivo


def test_motivo_cita_todas_as_posicoes_faltando():
    pode, motivo = pode_concluir(
        "ia", [criterio(None), criterio(7), criterio(None)]
    )
    assert pode is False
    assert "#1" in motivo and "#3" in motivo
    assert "#2" not in motivo


def test_aceita_linha_do_banco_e_nao_so_dict():
    pode, _ = pode_concluir("ia", [ComoLinhaDoBanco(evidencia_id=3)])
    assert pode is True
    pode, _ = pode_concluir("ia", [ComoLinhaDoBanco()])
    assert pode is False


# ---------------------------------------------------------------- humano


@pytest.mark.parametrize("papel", ["admin", "lead", "dev"])
def test_humano_conclui_sem_evidencia(papel):
    """De proposito: a pessoa responde pelo que afirma.

    Travar o dev atras de um formulario faria o Falange atrapalhar o
    trabalho. O preco e a transparencia, nao a proibicao.
    """
    pode, motivo = pode_concluir(papel, [criterio(None)])
    assert pode is True
    assert motivo == ""


def test_humano_conclui_task_sem_criterio():
    assert pode_concluir("dev", [])[0] is True


# ------------------------------------------------- marca de transparencia


def test_marca_sem_evidencia_quando_falta_prova():
    assert concluida_sem_evidencia([criterio(1), criterio(None)]) is True


def test_nao_marca_quando_tudo_tem_prova():
    assert concluida_sem_evidencia([criterio(1), criterio(2)]) is False


def test_task_sem_criterio_conta_como_sem_evidencia():
    # Nao ha prova de nada: dizer o contrario esconderia o caso mais fraco.
    assert concluida_sem_evidencia([]) is True


def test_posicoes_sao_1_based_para_casar_com_o_card():
    assert criterios_sem_prova([criterio(None), criterio(1)]) == [1]
    assert criterios_sem_prova([criterio(1), criterio(None)]) == [2]
