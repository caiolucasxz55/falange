"""Throughput e tempo de ciclo a partir dos eventos.

Modulo puro, entao nada precisa de banco. O que estes testes prendem e a
diferenca entre contar o EVENTO e olhar o estado atual -- e justamente
nessa diferenca que mora o motivo de a tabela de eventos existir.
"""

from datetime import date, datetime, timedelta, timezone

from backend.dominio.evolucao import (
    MINIMO_PARA_TENDENCIA,
    ciclos,
    contagem_por_tipo,
    inicio_da_semana,
    montar,
    semanas,
    tempo_de_ciclo,
    throughput,
)

# Uma terca-feira, para a conta de "segunda da semana" nao passar por sorte.
AGORA = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)
SEGUNDA = date(2026, 11, 2)

_proximo_id = [0]


def evento(tipo, task_id=None, quando=None, **dados):
    _proximo_id[0] += 1
    return {
        "id": _proximo_id[0],
        "tipo": tipo,
        "task_id": task_id,
        "criado_em": quando or AGORA,
        "dados": dados,
    }


def status(task_id, para, quando=None, de="aberta"):
    return evento("task_mudou_status", task_id, quando, de=de, para=para)


# ------------------------------------------------------------- a semana


def test_a_semana_comeca_na_segunda():
    assert inicio_da_semana(AGORA) == SEGUNDA
    # Um domingo pertence a semana que comecou na segunda anterior.
    domingo = datetime(2026, 11, 8, 23, 0, tzinfo=timezone.utc)
    assert inicio_da_semana(domingo) == SEGUNDA


def test_a_grade_vem_da_mais_antiga_para_a_mais_nova():
    grade = semanas(AGORA, 3)
    assert grade == [date(2026, 10, 19), date(2026, 10, 26), SEGUNDA]


# --------------------------------------------------------- throughput


def test_conta_a_conclusao_por_semana():
    eventos = [
        status(1, "concluida"),
        status(2, "concluida"),
        status(3, "concluida", AGORA - timedelta(weeks=1)),
    ]
    saida = throughput(eventos, ate=AGORA, quantas_semanas=2)
    assert saida["concluidas"] == [1, 2]


def test_so_a_transicao_para_concluida_conta():
    eventos = [
        status(1, "em_andamento"),
        status(2, "aberta"),
        status(3, "concluida"),
        evento("task_criada", 4),
    ]
    assert throughput(eventos, ate=AGORA, quantas_semanas=1)["concluidas"] == [1]


def test_task_reaberta_e_concluida_de_novo_conta_duas_vezes():
    """O motivo de contar o evento, e nao o estado.

    Olhando so a task, ela esta concluida uma vez. Mas o time entregou
    duas vezes -- e e a entrega que o throughput mede.
    """
    eventos = [
        status(1, "concluida", AGORA - timedelta(weeks=1)),
        status(1, "em_andamento", AGORA - timedelta(days=3), de="concluida"),
        status(1, "concluida", AGORA),
    ]
    saida = throughput(eventos, ate=AGORA, quantas_semanas=2)
    assert saida["concluidas"] == [1, 1]


def test_separa_por_bloco_usando_a_task():
    tasks = {1: {"bloco": "backend"}, 2: {"bloco": "frontend"}}
    eventos = [status(1, "concluida"), status(2, "concluida")]
    saida = throughput(eventos, tasks, ate=AGORA, quantas_semanas=1)
    assert saida["por_bloco"] == {"backend": [1], "frontend": [1]}


def test_task_apagada_nao_some_do_throughput():
    """A FK do evento e SET NULL: a entrega continua contada.

    Apagar a task depois nao desfaz o fato de ela ter sido entregue
    naquela semana -- e o grafico ficaria mentindo se desfizesse.
    """
    saida = throughput([status(None, "concluida")], {}, ate=AGORA, quantas_semanas=1)
    assert saida["concluidas"] == [1]
    assert saida["por_bloco"] == {"sem bloco": [1]}


def test_evento_fora_da_janela_fica_de_fora():
    antigo = status(1, "concluida", AGORA - timedelta(weeks=20))
    saida = throughput([antigo], ate=AGORA, quantas_semanas=4)
    assert saida["concluidas"] == [0, 0, 0, 0]


# ------------------------------------------------------ tempo de ciclo


def test_mede_de_em_andamento_ate_concluida():
    eventos = [
        status(1, "em_andamento", AGORA - timedelta(days=3)),
        status(1, "concluida", AGORA),
    ]
    assert ciclos(eventos) == {1: [3.0]}


def test_task_concluida_sem_passar_por_em_andamento_nao_tem_ciclo():
    """Medir isso como zero sujaria a mediana com o que nao foi medido."""
    assert ciclos([status(1, "concluida")]) == {}


def test_dois_ciclos_na_mesma_task_sao_medidos_separados():
    """O que `iniciada_em`/`concluida_em` nao consegue contar.

    A task guarda so o PRIMEIRO inicio e a ULTIMA conclusao, entao ela
    mediria o intervalo inteiro -- incluindo os dias em que o trabalho
    ja estava pronto e so esperava.
    """
    eventos = [
        status(1, "em_andamento", AGORA - timedelta(days=10)),
        status(1, "concluida", AGORA - timedelta(days=9)),
        status(1, "em_andamento", AGORA - timedelta(days=2), de="concluida"),
        status(1, "concluida", AGORA),
    ]
    assert ciclos(eventos) == {1: [1.0, 2.0]}


def test_voltar_para_em_andamento_nao_reinicia_a_contagem():
    eventos = [
        status(1, "em_andamento", AGORA - timedelta(days=5)),
        status(1, "em_andamento", AGORA - timedelta(days=1)),
        status(1, "concluida", AGORA),
    ]
    assert ciclos(eventos) == {1: [5.0]}


def test_eventos_fora_de_ordem_nao_produzem_ciclo_negativo():
    eventos = [
        status(1, "concluida", AGORA),
        status(1, "em_andamento", AGORA - timedelta(days=4)),
    ]
    # Ordenados por tempo antes de medir.
    assert ciclos(eventos) == {1: [4.0]}


def test_a_mediana_vem_com_quantos_a_sustentam():
    eventos = []
    for i, dias in enumerate([1, 3, 5], start=1):
        eventos.append(status(i, "em_andamento", AGORA - timedelta(days=dias)))
        eventos.append(status(i, "concluida", AGORA))
    saida = tempo_de_ciclo(eventos)
    assert saida["mediana_dias"] == 3.0
    assert saida["n"] == 3
    assert saida["mais_rapido"] == 1.0
    assert saida["mais_lento"] == 5.0


def test_sem_ciclo_fechado_a_mediana_e_nula_e_nao_zero():
    """Zero diria "o time entrega instantaneamente". Nulo diz "nao sei"."""
    saida = tempo_de_ciclo([status(1, "em_andamento")])
    assert saida["mediana_dias"] is None
    assert saida["n"] == 0


# ------------------------------------------------------------- panorama


def test_conta_por_tipo():
    eventos = [evento("task_criada", 1), evento("task_criada", 2), status(1, "aberta")]
    assert contagem_por_tipo(eventos) == {"task_criada": 2, "task_mudou_status": 1}


def test_pouco_historico_avisa_em_vez_de_desenhar_nada():
    """Grafico quase vazio parece "o time parou"; o aviso diz o que houve."""
    saida = montar([evento("task_criada", 1)], ate=AGORA)
    assert "aviso" in saida
    assert "1 eventos" in saida["aviso"]


def test_com_historico_suficiente_nao_avisa():
    eventos = [evento("task_criada", i) for i in range(MINIMO_PARA_TENDENCIA)]
    assert "aviso" not in montar(eventos, ate=AGORA)


def test_aceita_objeto_do_orm_e_nao_so_dict():
    """A rota passa o model; o dominio nao pode exigir conversao antes."""
    from types import SimpleNamespace

    from backend.models import TipoEvento

    linha = SimpleNamespace(
        id=1,
        tipo=TipoEvento.task_mudou_status,
        task_id=7,
        criado_em=AGORA,
        dados={"para": "concluida"},
    )
    assert throughput([linha], ate=AGORA, quantas_semanas=1)["concluidas"] == [1]


# ------------------------------------- o que a janela deixa de fora


def test_conclusao_sem_inicio_na_janela_e_contada():
    """O ciclo longo some, e o numero tem de dizer que sumiu.

    A janela precisa das DUAS pontas. Quando o `em_andamento` ficou para
    tras, o ciclo e descartado -- e so o longo e descartado, entao a
    mediana fica enviesada para baixo. Descartar e certo; descartar em
    silencio nao.
    """
    saida = tempo_de_ciclo([status(1, "concluida")])
    assert saida["n"] == 0
    assert saida["sem_inicio_na_janela"] == 1


def test_ciclo_completo_nao_conta_como_sem_inicio():
    eventos = [
        status(1, "em_andamento", AGORA - timedelta(days=2)),
        status(1, "concluida", AGORA),
    ]
    saida = tempo_de_ciclo(eventos)
    assert saida["n"] == 1
    assert saida["sem_inicio_na_janela"] == 0


def test_os_dois_casos_convivem_na_mesma_resposta():
    """Um ciclo medido e um perdido: a mediana sai E o aviso sai."""
    eventos = [
        status(1, "em_andamento", AGORA - timedelta(days=4)),
        status(1, "concluida", AGORA),
        status(2, "concluida", AGORA),  # comecou antes da janela
    ]
    saida = tempo_de_ciclo(eventos)
    assert saida["mediana_dias"] == 4.0
    assert saida["n"] == 1
    assert saida["sem_inicio_na_janela"] == 1


def test_reconclusao_nao_conta_como_sem_inicio():
    """Concluir, reabrir e concluir de novo tem inicio para os dois ciclos."""
    eventos = [
        status(1, "em_andamento", AGORA - timedelta(days=9)),
        status(1, "concluida", AGORA - timedelta(days=8)),
        status(1, "em_andamento", AGORA - timedelta(days=3), de="concluida"),
        status(1, "concluida", AGORA),
    ]
    saida = tempo_de_ciclo(eventos)
    assert saida["n"] == 2
    assert saida["sem_inicio_na_janela"] == 0
