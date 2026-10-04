"""Motor de priorizacao: decide o que vale a pena fazer agora.

Modulo puro. Nao abre sessao, nao faz HTTP, nao conhece ORM: recebe dados e
devolve dados. Assim o mesmo calculo serve o endpoint, o frontend e a IA, e
da para testar sem banco.

Nada de peso escondido em prompt: todo numero esta em PESOS ou nas constantes
logo abaixo, com o porque ao lado.
"""

from datetime import datetime
from typing import Any, Optional

PESOS = {
    # Prioridade declarada pelo time: e a intencao explicita, pesa mais.
    "prioridade_alta": 30,
    "prioridade_media": 15,
    "prioridade_baixa": 0,
    # Cada task que esta esperando por esta aqui. Destravar o time vale mais
    # que avancar sozinho, por isso o peso alto por dependente.
    "destrava_por_task": 10,
    "destrava_teto": 40,
    # Idade evita que task boa fique esquecida para sempre, mas nao pode
    # dominar o ranking: o teto equivale a 15 dias.
    "idade_por_dia": 1,
    "idade_teto": 15,
    # Empurrao pequeno para o que sai rapido e tira uma pendencia do caminho.
    "quick_win": 5,
}

# Acima disso, "muita coisa e alta" deixa de ser prioridade e vira ruido.
LIMITE_INFLACAO = 0.4

# Dias em em_andamento sem concluir ate virar sinal de trabalho parado.
DIAS_PARADA = 5

_ABERTAS = ("aberta", "em_andamento")


# Campos que chegam como Enum quando a origem e o ORM. Enum de str compara
# igual a string, mas quebra como chave de dict e imprime "Prioridade.baixa",
# entao normaliza na entrada e o resto do modulo so ve texto.
_CAMPOS_ENUM = ("prioridade", "estimativa", "bloco", "status")


def _texto(valor: Any) -> Any:
    return getattr(valor, "value", valor)


def _normalizar(tasks: list[dict]) -> list[dict]:
    return [{**t, **{c: _texto(t.get(c)) for c in _CAMPOS_ENUM}} for t in tasks]


def _dias(de: Optional[datetime], ate: datetime) -> float:
    if de is None:
        return 0.0
    return max(0.0, (ate - de).total_seconds() / 86400)


def _dependentes_transitivos(tasks: list[dict]) -> dict[int, list[int]]:
    """Para cada task, quem espera por ela direta ou transitivamente.

    Se A trava B e B trava C, A destrava [B, C]. Tasks concluidas nao contam:
    quem ja terminou nao esta esperando ninguem.
    """
    diretos: dict[int, list[int]] = {}
    for task in tasks:
        travadora = task.get("bloqueada_por")
        if travadora is not None and task.get("status") != "concluida":
            diretos.setdefault(travadora, []).append(task["id"])

    def descer(raiz: int) -> list[int]:
        vistos: list[int] = []
        fila = list(diretos.get(raiz, []))
        while fila:
            atual = fila.pop(0)
            # Ciclo nao existe (o backend recusa), mas a guarda e barata.
            if atual in vistos or atual == raiz:
                continue
            vistos.append(atual)
            fila.extend(diretos.get(atual, []))
        return sorted(vistos)

    return {task["id"]: descer(task["id"]) for task in tasks}


def _alerta_inversao(tasks: list[dict], dependentes: dict[int, list[int]]) -> list[dict]:
    """Task de prioridade menor travando uma alta: a fila esta invertida."""
    por_id = {t["id"]: t for t in tasks}
    alertas = []
    for task in tasks:
        if task.get("prioridade") == "alta" or task.get("status") == "concluida":
            continue
        travadas_altas = [
            outro
            for outro in dependentes.get(task["id"], [])
            if por_id.get(outro, {}).get("prioridade") == "alta"
        ]
        if travadas_altas:
            lista = ", ".join(f"#{i}" for i in travadas_altas)
            alertas.append(
                {
                    "tipo": "inversao",
                    "task_id": task["id"],
                    "mensagem": (
                        f"#{task['id']} esta como {task.get('prioridade')} mas trava "
                        f"{lista} (alta); considere subir a prioridade dela"
                    ),
                    "tasks_afetadas": travadas_altas,
                }
            )
    return alertas


def ranquear(
    tasks: list[dict],
    agora: datetime,
    cargas: Optional[dict[str, dict]] = None,
    responsavel: Optional[str] = None,
) -> dict[str, Any]:
    """Ordena o que da para fazer agora e explica cada escolha.

    Entram so tasks aberta/em_andamento que nao estao bloqueadas: o que esta
    travado nao e escolha do dev, e sim consequencia.

    Devolve {"sugestoes", "alertas", "avisos"}. Cada sugestao traz `score` e
    `motivos` em frases curtas, para a IA explicar sem inventar razao.
    """
    cargas = cargas or {}
    tasks = _normalizar(tasks)
    dependentes = _dependentes_transitivos(tasks)

    candidatas = [
        t
        for t in tasks
        if t.get("status") in _ABERTAS and t.get("bloqueada_por") is None
    ]

    sugestoes = []
    for task in candidatas:
        motivos: list[str] = []
        score = 0

        prioridade = task.get("prioridade", "media")
        peso_prioridade = PESOS.get(f"prioridade_{prioridade}", 0)
        score += peso_prioridade
        if peso_prioridade:
            motivos.append(f"prioridade {prioridade}")

        espera = dependentes.get(task["id"], [])
        if espera:
            bruto = len(espera) * PESOS["destrava_por_task"]
            score += min(bruto, PESOS["destrava_teto"])
            lista = ", ".join(f"#{i}" for i in espera)
            plural = "tasks" if len(espera) > 1 else "task"
            motivos.append(f"destrava {len(espera)} {plural} ({lista})")

        dias = int(_dias(task.get("criada_em"), agora))
        if dias:
            score += min(dias * PESOS["idade_por_dia"], PESOS["idade_teto"])
            motivos.append(f"aberta ha {dias} dias")

        if task.get("estimativa") == "PP":
            score += PESOS["quick_win"]
            motivos.append("quick win (PP)")

        # Trabalho comecado tem precedencia sobre trabalho novo: troca de
        # contexto custa caro. Entra como chave de ordenacao, nao como score,
        # para nao distorcer a comparacao entre as demais.
        primeiro = (
            responsavel is not None
            and task.get("responsavel") == responsavel
            and task.get("status") == "em_andamento"
        )
        if primeiro:
            motivos.append("termine antes de comecar")

        sugestoes.append(
            {
                "id": task["id"],
                "titulo": task.get("titulo"),
                "prioridade": prioridade,
                "estimativa": task.get("estimativa"),
                "bloco": task.get("bloco"),
                "responsavel": task.get("responsavel"),
                "status": task.get("status"),
                "score": score,
                "motivos": motivos,
                "destrava": espera,
                "_primeiro": primeiro,
            }
        )

    # Empate resolvido pelo id: resultado estavel, sem aleatoriedade.
    sugestoes.sort(key=lambda s: (not s["_primeiro"], -s["score"], s["id"]))
    for sugestao in sugestoes:
        del sugestao["_primeiro"]

    alertas = _alerta_inversao(tasks, dependentes)

    abertas = [t for t in tasks if t.get("status") in _ABERTAS]
    altas = [t for t in abertas if t.get("prioridade") == "alta"]
    if abertas and len(altas) / len(abertas) > LIMITE_INFLACAO:
        porcento = round(100 * len(altas) / len(abertas))
        alertas.append(
            {
                "tipo": "inflacao",
                "task_id": None,
                "mensagem": (
                    f"{porcento}% das abertas estao como alta "
                    f"({len(altas)} de {len(abertas)}); se tudo e prioridade, nada e"
                ),
                "tasks_afetadas": sorted(t["id"] for t in altas),
            }
        )

    for task in tasks:
        if task.get("status") != "em_andamento":
            continue
        parada = _dias(task.get("iniciada_em"), agora)
        if task.get("iniciada_em") is not None and parada > DIAS_PARADA:
            alertas.append(
                {
                    "tipo": "parada",
                    "task_id": task["id"],
                    "mensagem": (
                        f"#{task['id']} esta em andamento ha {int(parada)} dias; "
                        "trabalho parado ou esquecido"
                    ),
                    "tasks_afetadas": [task["id"]],
                }
            )

    avisos = []
    if responsavel is not None:
        carga = cargas.get(responsavel)
        if carga and carga.get("sobrecarregado"):
            avisos.append(
                f"{responsavel} ja tem {carga.get('tasks_abertas')} tasks abertas "
                f"(limite {carga.get('limite')}); considere terminar antes de pegar mais"
            )

    return {"sugestoes": sugestoes, "alertas": alertas, "avisos": avisos}
