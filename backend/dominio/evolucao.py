"""Como o time esta andando: throughput, tempo de ciclo e o que mudou.

Modulo puro. Recebe eventos e tasks, devolve numeros.

A diferenca para `calibracao.py` e o sujeito: a calibracao pergunta "a
estimativa deste time bate com a realidade?"; aqui a pergunta e "o time
esta entregando mais ou menos que antes, e quanto tempo leva do comeco ao
fim?". Uma julga a previsao, a outra julga o fluxo.

## Semana comeca na segunda

Nao e detalhe estetico: com semanas comecando em dias diferentes, duas
leituras do mesmo periodo dao numeros diferentes e ninguem sabe qual esta
certo. Segunda e o inicio da semana de trabalho na maior parte dos lugares
onde isto vai rodar.

## O que nao da para saber

O tempo de ciclo sai dos eventos de mudanca de status, nao de
`iniciada_em`/`concluida_em`. Parece redundante, mas nao e: a task guarda
so o PRIMEIRO inicio e a ULTIMA conclusao, entao uma task reaberta e
concluida de novo mede o intervalo inteiro, incluindo o tempo em que ela
estava pronta. O evento sabe de cada transicao.

Em compensacao, tasks mexidas ANTES de a tabela de eventos existir nao tem
historia nenhuma. Elas ficam de fora da conta, e `eventos_no_periodo` diz
quantos eventos sustentam o numero -- com pouco registro, quem le precisa
saber que o grafico e sobre pouca coisa, e nao que o time parou.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import median
from typing import Any, Iterable, Optional

# Quantos eventos sao poucos demais para o grafico dizer algo.
MINIMO_PARA_TENDENCIA = 10

SEMANAS_PADRAO = 8


def _texto(valor: Any) -> Any:
    return getattr(valor, "value", valor)


def _campo(obj: Any, nome: str, padrao=None):
    """Le de dict ou de objeto: o dominio aceita os dois."""
    if isinstance(obj, dict):
        return obj.get(nome, padrao)
    return getattr(obj, nome, padrao)


def inicio_da_semana(momento: datetime) -> date:
    """A segunda-feira da semana de `momento`."""
    dia = momento.date()
    return dia - timedelta(days=dia.weekday())


def semanas(ate: datetime, quantas: int = SEMANAS_PADRAO) -> list[date]:
    """As `quantas` segundas-feiras ate a semana de `ate`, da mais antiga."""
    atual = inicio_da_semana(ate)
    return [atual - timedelta(weeks=i) for i in range(quantas - 1, -1, -1)]


def throughput(
    eventos: Iterable[Any],
    tasks_por_id: Optional[dict[int, Any]] = None,
    ate: Optional[datetime] = None,
    quantas_semanas: int = SEMANAS_PADRAO,
) -> dict:
    """Quantas tasks foram concluidas por semana, e por bloco.

    Conta o EVENTO de conclusao, nao o estado da task: assim uma task
    concluida, reaberta e concluida de novo aparece nas duas semanas em
    que foi entregue -- que e o que de fato aconteceu.
    """
    ate = ate or datetime.now(timezone.utc)
    tasks_por_id = tasks_por_id or {}
    grade = semanas(ate, quantas_semanas)
    conhecidas = set(grade)

    por_semana: dict[date, int] = {s: 0 for s in grade}
    por_bloco: dict[str, dict[date, int]] = defaultdict(
        lambda: {s: 0 for s in grade}
    )

    for evento in eventos:
        if _texto(_campo(evento, "tipo")) != "task_mudou_status":
            continue
        dados = _campo(evento, "dados") or {}
        if dados.get("para") != "concluida":
            continue

        semana = inicio_da_semana(_campo(evento, "criado_em"))
        if semana not in conhecidas:
            continue

        por_semana[semana] += 1
        task = tasks_por_id.get(_campo(evento, "task_id"))
        bloco = _texto(_campo(task, "bloco")) if task is not None else None
        por_bloco[bloco or "sem bloco"][semana] += 1

    return {
        "semanas": [s.isoformat() for s in grade],
        "concluidas": [por_semana[s] for s in grade],
        "por_bloco": {
            bloco: [contagem[s] for s in grade]
            for bloco, contagem in sorted(por_bloco.items())
        },
    }


def ciclos(eventos: Iterable[Any]) -> dict[int, list[float]]:
    """Duracao de cada ciclo fechado, por task, em dias.

    Um ciclo e `em_andamento` -> `concluida`. A task que nunca entrou em
    andamento nao tem ciclo: foi concluida sem ser comecada, e medir isso
    como "zero dias" sujaria a mediana com trabalho que nao foi medido.
    """
    # Ordenados por tempo: a sequencia de transicoes e o dado, e eventos
    # fora de ordem produziriam ciclos negativos.
    ordenados = sorted(
        (
            e
            for e in eventos
            if _texto(_campo(e, "tipo")) == "task_mudou_status"
        ),
        key=lambda e: (_campo(e, "criado_em"), _campo(e, "id") or 0),
    )

    comeco: dict[int, datetime] = {}
    fechados: dict[int, list[float]] = defaultdict(list)

    for evento in ordenados:
        task_id = _campo(evento, "task_id")
        if task_id is None:
            continue
        para = (_campo(evento, "dados") or {}).get("para")
        quando = _campo(evento, "criado_em")

        if para == "em_andamento":
            # So o PRIMEIRO inicio do ciclo: voltar para em_andamento duas
            # vezes seguidas nao reinicia a contagem.
            comeco.setdefault(task_id, quando)
        elif para == "concluida" and task_id in comeco:
            dias = (quando - comeco.pop(task_id)).total_seconds() / 86400
            if dias >= 0:
                fechados[task_id].append(round(dias, 2))

    return dict(fechados)


def conclusoes_sem_inicio(eventos: Iterable[Any]) -> int:
    """Conclusoes cujo `em_andamento` nao esta na janela lida.

    Um ciclo precisa das DUAS pontas. Quando a janela comeca depois do
    inicio -- ciclo longo, ou task comecada antes de a tabela de eventos
    existir -- a conclusao aparece sozinha e o ciclo e descartado.

    Descartar e o certo (nao da para medir o que nao se viu comecar), mas
    descartar em SILENCIO nao e: some justamente o ciclo LONGO, e a
    mediana fica enviesada para baixo sem nada indicando. Por isso este
    numero sai junto da mediana.
    """
    ordenados = sorted(
        (e for e in eventos if _texto(_campo(e, "tipo")) == "task_mudou_status"),
        key=lambda e: (_campo(e, "criado_em"), _campo(e, "id") or 0),
    )
    comecadas: set[int] = set()
    orfas = 0
    for evento in ordenados:
        task_id = _campo(evento, "task_id")
        if task_id is None:
            continue
        para = (_campo(evento, "dados") or {}).get("para")
        if para == "em_andamento":
            comecadas.add(task_id)
        elif para == "concluida":
            if task_id in comecadas:
                comecadas.discard(task_id)
            else:
                orfas += 1
    return orfas


def tempo_de_ciclo(eventos: Iterable[Any]) -> dict:
    """Mediana dos ciclos fechados, e quantos sustentam o numero."""
    eventos = list(eventos)
    todos = [d for lista in ciclos(eventos).values() for d in lista]
    orfas = conclusoes_sem_inicio(eventos)
    base = {"sem_inicio_na_janela": orfas}
    if not todos:
        return {
            **base,
            "mediana_dias": None,
            "n": 0,
            "mais_rapido": None,
            "mais_lento": None,
        }
    return {
        **base,
        "mediana_dias": round(median(todos), 2),
        "n": len(todos),
        "mais_rapido": min(todos),
        "mais_lento": max(todos),
    }


def contagem_por_tipo(eventos: Iterable[Any]) -> dict[str, int]:
    contagem: dict[str, int] = defaultdict(int)
    for evento in eventos:
        contagem[_texto(_campo(evento, "tipo"))] += 1
    return dict(sorted(contagem.items()))


def montar(
    eventos: Iterable[Any],
    tasks_por_id: Optional[dict[int, Any]] = None,
    ate: Optional[datetime] = None,
    quantas_semanas: int = SEMANAS_PADRAO,
) -> dict:
    """O panorama inteiro, com um aviso quando ha pouco historico."""
    eventos = list(eventos)
    saida = {
        "throughput": throughput(eventos, tasks_por_id, ate, quantas_semanas),
        "tempo_de_ciclo": tempo_de_ciclo(eventos),
        "por_tipo": contagem_por_tipo(eventos),
        "eventos_no_periodo": len(eventos),
    }
    if len(eventos) < MINIMO_PARA_TENDENCIA:
        # Dito em vez de desenhado: um grafico quase vazio parece "o time
        # parou", quando o que houve foi o registro ter comecado agora.
        saida["aviso"] = (
            f"so {len(eventos)} eventos registrados; o historico comeca "
            "quando a tabela de eventos passou a existir, entao o que "
            "aconteceu antes disso nao aparece aqui"
        )
    return saida
