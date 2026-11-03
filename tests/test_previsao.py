"""Previsao de marco: no prazo, em risco ou atrasado, com a conta exposta.

Modulo puro, entao nada aqui precisa de banco. O que estes testes prendem
e a CONTA -- um veredito sem numero defensavel nao serve para nada, e e
facil um refactor trocar o numero sem trocar a palavra.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from backend.dominio.calibracao import AMOSTRA_MINIMA
from backend.dominio.previsao import (
    ATRASADO,
    CONCLUIDO,
    EM_RISCO,
    NO_PRAZO,
    SEM_DATA,
    dias_por_classe,
    prever,
    trabalho_restante,
)

AGORA = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def task(estimativa="P", status="aberta"):
    return {"estimativa": estimativa, "status": status}


def marco(data_alvo=None, fechado_em=None, nome="Entrega"):
    return {"nome": nome, "data_alvo": data_alvo, "fechado_em": fechado_em}


def calibracao(**por_classe):
    """Calibracao no formato que `dominio/calibracao.py` devolve."""
    return {
        "por_estimativa": {
            classe: {"n": n, "mediana_dias": mediana}
            for classe, (n, mediana) in por_classe.items()
        }
    }


# --------------------------------------------------- quanto vale cada classe


def test_sem_calibracao_usa_a_faixa_nominal_pelo_lado_pessimista():
    """Sem dado, errar para o pessimista avisa cedo.

    Errar para o otimista avisaria quando nao desse mais tempo de fazer
    nada -- que e o pior momento possivel para um aviso de prazo.
    """
    valores = dias_por_classe(None)
    assert valores["PP"] == 0.5   # maximo da faixa, nao o meio
    assert valores["P"] == 1.5
    assert valores["M"] == 4.0
    assert valores["G"] == 8.0    # ponta aberta: o dobro do minimo


def test_com_amostra_usa_a_mediana_medida():
    valores = dias_por_classe(calibracao(P=(AMOSTRA_MINIMA, 3.0)))
    assert valores["P"] == 3.0
    # As outras classes seguem na nominal.
    assert valores["M"] == 4.0


def test_amostra_pequena_nao_vale():
    """Abaixo do minimo, a mediana e barulho -- a mesma regra da calibracao."""
    valores = dias_por_classe(calibracao(P=(AMOSTRA_MINIMA - 1, 9.0)))
    assert valores["P"] == 1.5


# ------------------------------------------------------- trabalho restante


def test_soma_so_o_que_esta_aberto():
    tasks = [
        task("P"),
        task("P", status="em_andamento"),
        task("G", status="concluida"),
    ]
    saida = trabalho_restante(tasks)
    assert saida["dias"] == 3.0  # 1.5 + 1.5; a G concluida nao entra


def test_task_em_andamento_conta_inteira():
    """Descontar metade por otimismo seria inventar dado.

    Nao ha como saber quanto de uma task em andamento ja foi feito.
    """
    assert trabalho_restante([task("M", status="em_andamento")])["dias"] == 4.0


def test_a_conta_sai_detalhada_por_classe():
    saida = trabalho_restante([task("P"), task("P"), task("M")])
    assert saida["por_classe"]["P"] == {"tasks": 2, "dias_cada": 1.5, "dias": 3.0}
    assert saida["por_classe"]["M"] == {"tasks": 1, "dias_cada": 4.0, "dias": 4.0}
    assert saida["dias"] == 7.0


def test_estimativa_ausente_nao_derruba_a_conta():
    saida = trabalho_restante([{"status": "aberta"}])
    assert saida["dias"] == 4.0  # cai em M, o meio da escala


# ------------------------------------------------------------- o veredito


def test_folga_confortavel_fica_no_prazo():
    # 1 task P = 1.5 dias de trabalho, 30 dias de calendario.
    saida = prever(marco(date(2026, 12, 3)), [task("P")], agora=AGORA)
    assert saida["veredito"] == NO_PRAZO
    assert saida["dias_ate_alvo"] == 30
    assert "1.5 dias de trabalho para 30" in saida["motivo"]


def test_passar_de_80_por_cento_do_tempo_e_risco():
    """Chegar raspando nao e "no prazo": e aviso que chegou tarde."""
    # 4 dias de trabalho (1 M) para 4 de calendario: cabe, mas sem folga.
    saida = prever(marco(AGORA.date() + timedelta(days=4)), [task("M")], agora=AGORA)
    assert saida["veredito"] == EM_RISCO
    assert "sem folga" in saida["motivo"]


def test_exatamente_80_por_cento_ainda_e_no_prazo():
    """A fronteira, fixada de proposito: o limiar e "PASSA de 80%".

    4 dias de trabalho em 5 de calendario deixa um dia inteiro de folga.
    Chamar isso de risco encheria o painel de alarme e ensinaria o time a
    ignorar a cor.
    """
    saida = prever(marco(AGORA.date() + timedelta(days=5)), [task("M")], agora=AGORA)
    assert saida["veredito"] == NO_PRAZO


def test_trabalho_maior_que_o_calendario_e_atraso():
    saida = prever(
        marco(date(2026, 11, 5)), [task("M"), task("M")], agora=AGORA
    )
    assert saida["veredito"] == ATRASADO
    assert "8.0 dias de trabalho restante para 2" in saida["motivo"]


def test_data_passada_com_task_aberta_e_atraso():
    saida = prever(marco(date(2026, 11, 1)), [task("PP")], agora=AGORA)
    assert saida["veredito"] == ATRASADO
    assert saida["dias_ate_alvo"] == -2
    assert "passou ha 2 dia(s)" in saida["motivo"]


def test_data_passada_sem_task_aberta_nao_e_atraso():
    """Tudo pronto e tudo pronto, mesmo que a data tenha passado.

    Acusar atraso aqui seria cobrar por um prazo que foi cumprido.
    """
    saida = prever(marco(date(2026, 11, 1)), [task("P", status="concluida")], agora=AGORA)
    assert saida["veredito"] == NO_PRAZO


def test_marco_sem_data_nao_recebe_veredito_de_prazo():
    """Dizer "no prazo" sem prazo seria uma garantia que ninguem deu."""
    saida = prever(marco(None), [task("G")], agora=AGORA)
    assert saida["veredito"] == SEM_DATA
    assert saida["dias_ate_alvo"] is None


def test_marco_fechado_sai_como_concluido():
    saida = prever(
        marco(date(2026, 11, 1), fechado_em=AGORA), [task("P")], agora=AGORA
    )
    assert saida["veredito"] == CONCLUIDO


def test_a_calibracao_muda_o_veredito():
    """O ponto de usar a calibracao: o mesmo marco muda de cor com os dados.

    Se o time leva 5 dias no que chama de P, 3 tasks P nao cabem em 10
    dias -- mesmo que a faixa nominal dissesse que cabem com folga.
    """
    tres_p = [task("P"), task("P"), task("P")]
    alvo = marco(date(2026, 11, 13))  # 10 dias

    nominal = prever(alvo, tres_p, agora=AGORA)
    assert nominal["veredito"] == NO_PRAZO  # 4.5 dias para 10

    medido = prever(alvo, tres_p, calibracao(P=(AMOSTRA_MINIMA, 5.0)), agora=AGORA)
    assert medido["veredito"] == ATRASADO  # 15 dias para 10
    assert medido["dias_de_trabalho_restante"] == 15.0


def test_o_progresso_sai_junto():
    tasks = [task("P"), task("P", status="concluida"), task("M", status="concluida")]
    saida = prever(marco(date(2026, 12, 3)), tasks, agora=AGORA)
    assert saida["tasks_total"] == 3
    assert saida["tasks_concluidas"] == 2
    assert saida["tasks_abertas"] == 1


def test_aceita_enum_do_orm_e_nao_so_texto():
    """A rota passa o model; o dominio nao pode exigir conversao antes."""
    from backend.models.enums import Estimativa, Status

    saida = trabalho_restante(
        [{"estimativa": Estimativa.M, "status": Status.aberta}]
    )
    assert saida["dias"] == 4.0


def test_datetime_no_data_alvo_funciona_como_date():
    """O banco pode devolver date; um cliente pode mandar datetime."""
    saida = prever(
        marco(datetime(2026, 12, 3, tzinfo=timezone.utc)), [task("P")], agora=AGORA
    )
    assert saida["dias_ate_alvo"] == 30


@pytest.mark.parametrize(
    "veredito_esperado,dias", [(NO_PRAZO, 30), (EM_RISCO, 4), (ATRASADO, 2)]
)
def test_a_conta_aparece_sempre_no_motivo(veredito_esperado, dias):
    """Veredito sem numero e palpite, e palpite sobre prazo nao convence."""
    alvo = AGORA.date() + timedelta(days=dias)
    saida = prever(marco(alvo), [task("M")], agora=AGORA)
    assert saida["veredito"] == veredito_esperado
    assert str(saida["dias_de_trabalho_restante"]) in saida["motivo"]
    assert str(saida["dias_ate_alvo"]) in saida["motivo"]
