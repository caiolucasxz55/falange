"""Testes da calibracao de estimativa. Modulo puro: nao precisa de banco."""

from datetime import datetime, timedelta, timezone

from backend.calibracao import AMOSTRA_MINIMA, calibrar

INICIO = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


def concluida(estimativa, dias, bloco="backend", iniciada=True):
    """Task concluida que levou `dias` corridos entre iniciar e concluir."""
    return {
        "id": 1,
        "estimativa": estimativa,
        "bloco": bloco,
        "status": "concluida",
        "iniciada_em": INICIO if iniciada else None,
        "concluida_em": INICIO + timedelta(days=dias),
    }


def classe(saida, estimativa):
    return saida["por_estimativa"][estimativa]


def test_amostra_pequena_nao_vira_veredito():
    tasks = [concluida("P", 1.0) for _ in range(AMOSTRA_MINIMA - 1)]

    resultado = classe(calibrar(tasks), "P")

    assert resultado["n"] == AMOSTRA_MINIMA - 1
    assert resultado["veredito"] == "sem_dados"


def test_mediana_ignora_o_caso_extremo():
    # Quatro tasks de 1 dia e uma de 30: a media mentiria, a mediana nao.
    tasks = [concluida("P", 1.0) for _ in range(4)] + [concluida("P", 30.0)]

    resultado = classe(calibrar(tasks), "P")

    assert resultado["n"] == 5
    assert resultado["mediana_dias"] == 1.0
    assert resultado["veredito"] == "coerente"


def test_veredito_superestimada_quando_a_mediana_fica_abaixo_da_faixa():
    # M vale de 1.5 a 4 dias; na pratica saiu em 0.5.
    tasks = [concluida("M", 0.5) for _ in range(AMOSTRA_MINIMA)]

    assert classe(calibrar(tasks), "M")["veredito"] == "superestimada"


def test_veredito_subestimada_quando_a_mediana_passa_da_faixa():
    tasks = [concluida("P", 3.0) for _ in range(AMOSTRA_MINIMA)]

    assert classe(calibrar(tasks), "P")["veredito"] == "subestimada"


def test_veredito_coerente_dentro_da_faixa():
    tasks = [concluida("M", 2.0) for _ in range(AMOSTRA_MINIMA)]

    assert classe(calibrar(tasks), "M")["veredito"] == "coerente"


def test_mediana_no_limite_da_faixa_conta_como_coerente():
    # P vai ate 1.5 inclusive.
    tasks = [concluida("P", 1.5) for _ in range(AMOSTRA_MINIMA)]

    assert classe(calibrar(tasks), "P")["veredito"] == "coerente"


def test_pontas_abertas_nao_acusam_o_lado_que_nao_existe():
    # PP nao tem minimo: rapido demais nunca e superestimada.
    rapidas = [concluida("PP", 0.01) for _ in range(AMOSTRA_MINIMA)]
    assert classe(calibrar(rapidas), "PP")["veredito"] == "coerente"

    # G nao tem maximo: lento nunca e subestimada.
    lentas = [concluida("G", 40.0) for _ in range(AMOSTRA_MINIMA)]
    assert classe(calibrar(lentas), "G")["veredito"] == "coerente"


def test_task_sem_iniciada_em_e_ignorada():
    tasks = [concluida("P", 1.0, iniciada=False) for _ in range(AMOSTRA_MINIMA)]

    saida = calibrar(tasks)

    assert saida["n_total"] == 0
    assert classe(saida, "P")["n"] == 0
    assert classe(saida, "P")["veredito"] == "sem_dados"


def test_calibracao_por_bloco_e_independente_da_geral():
    # infra estoura a faixa de P; backend fica dentro dela.
    tasks = [concluida("P", 3.0, bloco="infra") for _ in range(AMOSTRA_MINIMA)]
    tasks += [concluida("P", 1.0, bloco="backend") for _ in range(AMOSTRA_MINIMA)]

    saida = calibrar(tasks)

    assert saida["por_bloco"]["infra"]["P"]["veredito"] == "subestimada"
    assert saida["por_bloco"]["backend"]["P"]["veredito"] == "coerente"
    # E por isso que o bloco importa: na mistura a mediana vai para 2.0 e
    # acusa o projeto inteiro por um problema que e so de infra.
    assert classe(saida, "P")["mediana_dias"] == 2.0
    assert classe(saida, "P")["veredito"] == "subestimada"


def test_bloco_sem_medida_nao_aparece():
    tasks = [concluida("P", 1.0, bloco="backend")]

    assert list(calibrar(tasks)["por_bloco"]) == ["backend"]
