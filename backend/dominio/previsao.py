"""Um marco vai dar no prazo?

Modulo puro. Nao abre sessao, nao faz HTTP: recebe o marco, as tasks dele e
a calibracao, e devolve um veredito com a CONTA EXPOSTA.

A conta exposta e o ponto. "Em risco" sem numero e palpite, e palpite de
software sobre prazo nao convence ninguem -- com razao. Aqui sai quantos
dias de trabalho restam, quantos dias de calendario ha ate a data, e de
onde veio cada numero. Quem discorda tem onde apontar.

## O que esta previsao NAO e

Ela soma a mediana de duracao de cada task aberta. Isso trata o time como
se fizesse uma task por vez e nao tivesse feriado, ferias nem reuniao.

A escolha e deliberada: a alternativa seria modelar capacidade por pessoa,
paralelismo e calendario, e um modelo desses erra com mais confianca. Uma
soma simples, com a conta a vista, erra de um jeito que a pessoa percebe e
corrige. Esta na docstring para ninguem achar que e mais do que e.

E uma duracao MEDIANA, nao um esforco: o projeto mede dias corridos entre
iniciar e concluir (ver `dominio/calibracao.py`), entao tempo parado ja
esta dentro do numero. Por isso somar medianas nao e tao otimista quanto
parece a primeira vista.
"""

from datetime import date, datetime, timezone
from typing import Any, Iterable, Optional

from backend.dominio.calibracao import AMOSTRA_MINIMA, FAIXAS

# Veredito, do melhor para o pior.
NO_PRAZO = "no_prazo"
EM_RISCO = "em_risco"
ATRASADO = "atrasado"
SEM_DATA = "sem_data"
CONCLUIDO = "concluido"

# Folga: o marco entra em risco quando o trabalho restante passa de 80% do
# tempo restante. Nao e 100% porque chegar raspando nao e "no prazo" -- e
# um aviso que chegou tarde demais para alguem fazer algo a respeito.
FOLGA = 0.8

# Quando a classe nao tem amostra, vale a faixa nominal. Usa o MAIOR valor
# da faixa, nao o meio: sem dado, errar para o lado pessimista avisa cedo;
# errar para o otimista avisa quando nao da mais tempo.
#
# `G` tem ponta aberta (4.0, None) e nao da para pegar o maximo: assume-se
# o dobro do minimo, que e o palpite mais honesto disponivel.
_NOMINAL_SEM_AMOSTRA = {
    classe: (maximo if maximo is not None else (minimo or 0) * 2)
    for classe, (minimo, maximo) in FAIXAS.items()
}

_ABERTAS = ("aberta", "em_andamento")


def _texto(valor: Any) -> Any:
    return getattr(valor, "value", valor)


def dias_por_classe(calibracao: Optional[dict]) -> dict[str, float]:
    """Quantos dias cada classe de estimativa vale, na pratica deste time.

    Usa a mediana medida quando ha amostra; a faixa nominal quando nao ha.
    E a mesma calibracao que a IA consulta antes de estimar -- previsao e
    estimativa tem de falar do mesmo numero, senao o painel contradiz a
    conversa.
    """
    por_classe = dict(_NOMINAL_SEM_AMOSTRA)
    medidas = ((calibracao or {}).get("por_estimativa") or {}) if calibracao else {}

    for classe, dados in medidas.items():
        if classe not in por_classe:
            continue
        mediana = (dados or {}).get("mediana_dias")
        if (dados or {}).get("n", 0) >= AMOSTRA_MINIMA and mediana:
            por_classe[classe] = float(mediana)
    return por_classe


def trabalho_restante(tasks: Iterable[dict], calibracao: Optional[dict] = None) -> dict:
    """Dias de trabalho ainda nao concluidos, e de onde o numero veio.

    So conta task ABERTA ou EM ANDAMENTO. Task em andamento conta inteira:
    nao ha como saber quanto dela ja foi, e descontar metade por otimismo
    seria inventar dado.
    """
    por_classe = dias_por_classe(calibracao)
    detalhe: dict[str, dict] = {}
    total = 0.0

    for task in tasks:
        if _texto(task.get("status")) not in _ABERTAS:
            continue
        classe = _texto(task.get("estimativa")) or "M"
        dias = por_classe.get(classe, _NOMINAL_SEM_AMOSTRA.get(classe, 1.0))
        total += dias
        entrada = detalhe.setdefault(
            classe, {"tasks": 0, "dias_cada": round(dias, 2), "dias": 0.0}
        )
        entrada["tasks"] += 1
        entrada["dias"] = round(entrada["dias"] + dias, 2)

    return {"dias": round(total, 2), "por_classe": detalhe}


def _dias_ate(data_alvo: date, hoje: date) -> int:
    return (data_alvo - hoje).days


def prever(
    marco: dict,
    tasks: Iterable[dict],
    calibracao: Optional[dict] = None,
    agora: Optional[datetime] = None,
) -> dict:
    """O veredito de um marco, com a conta a vista.

    `marco` precisa de `nome`, `data_alvo` (date ou None) e `fechado_em`.
    `tasks` sao as tasks DAQUELE marco, abertas e concluidas -- as
    concluidas entram na contagem para a tela poder mostrar progresso.
    """
    tasks = list(tasks)
    agora = agora or datetime.now(timezone.utc)
    hoje = agora.date()

    abertas = [t for t in tasks if _texto(t.get("status")) in _ABERTAS]
    concluidas = len(tasks) - len(abertas)
    restante = trabalho_restante(abertas, calibracao)

    base = {
        "nome": marco.get("nome"),
        "data_alvo": marco.get("data_alvo"),
        "tasks_total": len(tasks),
        "tasks_concluidas": concluidas,
        "tasks_abertas": len(abertas),
        "dias_de_trabalho_restante": restante["dias"],
        "por_classe": restante["por_classe"],
    }

    if marco.get("fechado_em") is not None:
        return {**base, "veredito": CONCLUIDO, "dias_ate_alvo": None, "motivo":
                "marco fechado"}

    data_alvo = marco.get("data_alvo")
    if data_alvo is None:
        # Sem data nao ha prazo para cumprir, e dizer "no prazo" seria uma
        # garantia que ninguem deu.
        return {
            **base,
            "veredito": SEM_DATA,
            "dias_ate_alvo": None,
            "motivo": "o marco nao tem data_alvo; nao da para prever nada",
        }

    if isinstance(data_alvo, datetime):
        data_alvo = data_alvo.date()
    dias_ate = _dias_ate(data_alvo, hoje)

    if not abertas:
        return {
            **base,
            "veredito": NO_PRAZO,
            "dias_ate_alvo": dias_ate,
            "motivo": "nao ha task aberta neste marco",
        }

    if dias_ate < 0:
        return {
            **base,
            "veredito": ATRASADO,
            "dias_ate_alvo": dias_ate,
            "motivo": (
                f"a data passou ha {abs(dias_ate)} dia(s) e ainda ha "
                f"{len(abertas)} task(s) aberta(s)"
            ),
        }

    if restante["dias"] > dias_ate:
        return {
            **base,
            "veredito": ATRASADO,
            "dias_ate_alvo": dias_ate,
            "motivo": (
                f"{restante['dias']} dias de trabalho restante para "
                f"{dias_ate} dia(s) de calendario"
            ),
        }

    if restante["dias"] > dias_ate * FOLGA:
        return {
            **base,
            "veredito": EM_RISCO,
            "dias_ate_alvo": dias_ate,
            "motivo": (
                f"{restante['dias']} dias de trabalho para {dias_ate} dia(s): "
                f"passa de {int(FOLGA * 100)}% do tempo, sem folga para imprevisto"
            ),
        }

    return {
        **base,
        "veredito": NO_PRAZO,
        "dias_ate_alvo": dias_ate,
        "motivo": (
            f"{restante['dias']} dias de trabalho para {dias_ate} dia(s) "
            "de calendario"
        ),
    }
