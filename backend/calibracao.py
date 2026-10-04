"""Calibracao de estimativa: compara o que o time estimou com o que levou.

Modulo puro. Nao abre sessao, nao faz HTTP: recebe tasks concluidas e devolve
o veredito por classe de estimativa.

O projeto ja grava `iniciada_em` e `concluida_em`, entao a duracao real sai de
graca. Isso e o Falange aprendendo: nenhum modelo guarda isso entre sessoes,
o banco guarda.
"""

from datetime import datetime
from statistics import median
from typing import Any, Optional

# Faixa nominal de cada estimativa, em DIAS CORRIDOS entre iniciar e concluir.
# Nao e esforco: uma task de duas horas que ficou tres dias parada mede tres
# dias. A calibracao mede o fluxo do time, nao o tamanho do codigo.
#
# (minimo, maximo); None e ponta aberta. Mediana exatamente no limite conta
# como coerente: nao vale acusar o time por um centesimo de dia.
FAIXAS: dict[str, tuple[Optional[float], Optional[float]]] = {
    "PP": (None, 0.5),
    "P": (0.5, 1.5),
    "M": (1.5, 4.0),
    "G": (4.0, None),
}

# Abaixo disso, qualquer conclusao seria barulho: 4 tasks nao fazem tendencia.
AMOSTRA_MINIMA = 5


def _duracao_dias(task: dict) -> Optional[float]:
    """Dias corridos entre iniciar e concluir, ou None se faltar marco."""
    inicio = task.get("iniciada_em")
    fim = task.get("concluida_em")
    if not isinstance(inicio, datetime) or not isinstance(fim, datetime):
        return None
    dias = (fim - inicio).total_seconds() / 86400
    return dias if dias >= 0 else None


def _texto(valor: Any) -> Any:
    """Enum do ORM chega como Enum; o resto do modulo so quer texto."""
    return getattr(valor, "value", valor)


def _avaliar(duracoes: list[float], estimativa: str) -> dict:
    minimo, maximo = FAIXAS[estimativa]
    faixa = {"minimo_dias": minimo, "maximo_dias": maximo}

    if len(duracoes) < AMOSTRA_MINIMA:
        return {
            "n": len(duracoes),
            "mediana_dias": round(median(duracoes), 2) if duracoes else None,
            "faixa": faixa,
            "veredito": "sem_dados",
        }

    meio = median(duracoes)
    if minimo is not None and meio < minimo:
        veredito = "superestimada"
    elif maximo is not None and meio > maximo:
        veredito = "subestimada"
    else:
        veredito = "coerente"

    return {
        "n": len(duracoes),
        "mediana_dias": round(meio, 2),
        "faixa": faixa,
        "veredito": veredito,
    }


def calibrar(tasks_concluidas: list[dict]) -> dict:
    """Veredito por estimativa e por bloco, a partir da duracao real.

    Entram so tasks com `iniciada_em` e `concluida_em`: sem os dois marcos
    nao da para medir, e chutar seria pior que nao responder.

    Devolve {"por_estimativa", "por_bloco", "amostra_minima", "n_total"}.
    """
    medidas: list[tuple[str, str, float]] = []
    for task in tasks_concluidas:
        dias = _duracao_dias(task)
        estimativa = _texto(task.get("estimativa"))
        if dias is None or estimativa not in FAIXAS:
            continue
        medidas.append((estimativa, _texto(task.get("bloco")), dias))

    por_estimativa = {
        estimativa: _avaliar([d for e, _, d in medidas if e == estimativa], estimativa)
        for estimativa in FAIXAS
    }

    por_bloco: dict[str, dict] = {}
    for bloco in sorted({b for _, b, _ in medidas if b}):
        do_bloco = {
            estimativa: _avaliar(
                [d for e, b, d in medidas if e == estimativa and b == bloco],
                estimativa,
            )
            for estimativa in FAIXAS
        }
        # So entra bloco com alguma classe medida; o resto seria ruido.
        if any(classe["n"] for classe in do_bloco.values()):
            por_bloco[bloco] = do_bloco

    return {
        "por_estimativa": por_estimativa,
        "por_bloco": por_bloco,
        "amostra_minima": AMOSTRA_MINIMA,
        "n_total": len(medidas),
    }
