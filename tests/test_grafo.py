"""Testes do grafo de dependencias. Modulo puro: nao precisa de banco.

Convencao das arestas: `(task, depende_de)` -- a primeira NAO anda enquanto
a segunda nao terminar.
"""

import pytest

from backend.dominio.grafo import (
    alcancaveis,
    bloqueada,
    cadeia,
    criaria_ciclo,
    depende_de,
    destrava,
    origem_da_cadeia,
    travando,
)

# A <- B <- C: C depende de B, que depende de A.
CORRENTE = [(2, 1), (3, 2)]

# D depende de duas pontas independentes.
LOSANGO = [(2, 1), (3, 1), (4, 2), (4, 3)]


# --------------------------------------------------------------------------
# vizinhanca
# --------------------------------------------------------------------------


def test_dependencias_diretas():
    assert depende_de(CORRENTE, 3) == [2]
    assert depende_de(CORRENTE, 1) == []


def test_varias_dependencias_na_mesma_task():
    # O ponto da fase: deixa de ser um ponteiro so.
    assert depende_de(LOSANGO, 4) == [2, 3]


def test_quem_esta_travando():
    assert travando(CORRENTE, 1) == [2]
    assert travando(LOSANGO, 1) == [2, 3]
    assert travando(LOSANGO, 4) == []


# --------------------------------------------------------------------------
# ciclos
# --------------------------------------------------------------------------


def test_task_nao_depende_de_si_mesma():
    assert criaria_ciclo([], 1, 1)


def test_ciclo_direto():
    # 1 ja depende de 2; fazer 2 depender de 1 fecha o ciclo.
    assert criaria_ciclo([(1, 2)], 2, 1)


def test_ciclo_transitivo():
    # C <- B <- A; fazer A depender de C fecha a volta.
    assert criaria_ciclo(CORRENTE, 1, 3)


def test_dependencia_legitima_nao_e_ciclo():
    assert not criaria_ciclo(CORRENTE, 1, 4)
    assert not criaria_ciclo(LOSANGO, 4, 1)


def test_losango_nao_e_ciclo():
    """Duas rotas ate a mesma task nao sao ciclo.

    Sem o conjunto de visitados a busca passaria duas vezes por 1 -- e num
    grafo maior isso vira explosao exponencial.
    """
    assert not criaria_ciclo(LOSANGO, 1, 5)


def test_a_busca_termina_mesmo_com_ciclo_ja_gravado():
    # Defesa: se um ciclo entrar por outro caminho, nada pode pendurar.
    ciclico = [(1, 2), (2, 3), (3, 1)]

    assert alcancaveis(ciclico, 1) == {1, 2, 3}


# --------------------------------------------------------------------------
# bloqueio derivado
# --------------------------------------------------------------------------


def test_bloqueada_enquanto_a_dependencia_nao_acaba():
    assert bloqueada(CORRENTE, 2, concluidas=set())


def test_deixa_de_ser_bloqueada_quando_a_dependencia_conclui():
    """O ponto de derivar em vez de guardar.

    Antes, concluir precisava LIMPAR o bloqueio de quem esperava; esquecer
    em algum caminho deixava task travada por algo que ja tinha acabado.
    """
    assert not bloqueada(CORRENTE, 2, concluidas={1})


def test_so_a_dependencia_direta_conta():
    # 3 depende de 2; 2 ainda nao acabou, mesmo com 1 concluida.
    assert bloqueada(CORRENTE, 3, concluidas={1})
    assert not bloqueada(CORRENTE, 3, concluidas={1, 2})


def test_uma_pendencia_entre_varias_ja_bloqueia():
    assert bloqueada(LOSANGO, 4, concluidas={2})
    assert not bloqueada(LOSANGO, 4, concluidas={2, 3})


def test_task_sem_dependencia_nunca_esta_bloqueada():
    assert not bloqueada(LOSANGO, 1, concluidas=set())


# --------------------------------------------------------------------------
# destrava: alimenta a priorizacao
# --------------------------------------------------------------------------


def test_destrava_quem_so_esperava_por_ela():
    assert destrava(CORRENTE, 1, concluidas=set()) == [2]


def test_nao_destrava_quem_ainda_tem_outra_pendencia():
    # Concluir 2 nao libera 4: ela ainda espera 3.
    assert destrava(LOSANGO, 2, concluidas=set()) == []


def test_destrava_quando_a_outra_pendencia_ja_acabou():
    assert destrava(LOSANGO, 2, concluidas={3}) == [4]


def test_quem_nao_trava_ninguem_destrava_nada():
    assert destrava(LOSANGO, 4, concluidas=set()) == []


# --------------------------------------------------------------------------
# cadeia: "o problema real esta la atras"
# --------------------------------------------------------------------------


def test_cadeia_mostra_tudo_que_falta():
    assert cadeia(CORRENTE, 3, concluidas=set()) == [1, 2]


def test_cadeia_ignora_o_que_ja_acabou():
    assert cadeia(CORRENTE, 3, concluidas={1}) == [2]
    assert cadeia(CORRENTE, 3, concluidas={1, 2}) == []


def test_origem_da_cadeia_e_a_pendencia_mais_funda():
    assert origem_da_cadeia(CORRENTE, 3, concluidas=set()) == 1


def test_origem_anda_junto_com_a_conclusao():
    assert origem_da_cadeia(CORRENTE, 3, concluidas={1}) == 2


def test_sem_pendencia_nao_ha_origem():
    assert origem_da_cadeia(CORRENTE, 3, concluidas={1, 2}) is None
    assert origem_da_cadeia(CORRENTE, 1, concluidas=set()) is None


def test_origem_com_empate_e_estavel():
    # 4 espera 2 e 3, as duas sem pendencia propria: devolve o menor id,
    # para a tela nao trocar de resposta a cada atualizacao.
    assert origem_da_cadeia(LOSANGO, 4, concluidas={1}) == 2


@pytest.mark.parametrize("task_id", [1, 2, 3, 4])
def test_grafo_vazio_nao_estoura(task_id):
    assert depende_de([], task_id) == []
    assert travando([], task_id) == []
    assert not bloqueada([], task_id, concluidas=set())
    assert destrava([], task_id, concluidas=set()) == []
