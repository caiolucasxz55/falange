"""Junta a task guardada com o que o grafo deriva.

Mora em `rotas/` porque e montagem de resposta, nao dado nem regra: o
repositorio devolve linhas, o dominio calcula sobre arestas, e e aqui que
os dois viram um `TaskOut`.

Existe para `depende_de`, `travando`, `bloqueada` e `criterios` sairem
iguais em toda rota que devolve task. Montar isso a mao em cada uma era o
caminho curto para uma responder diferente da outra.
"""

from typing import Iterable, Mapping, Optional

from backend.dominio import grafo
from backend.models import Criterio, Task
from backend.schemas import CriterioOut, TaskOut


def montar_task(
    task: Task,
    arestas: Iterable[tuple[int, int]],
    concluidas: set[int],
    criterios: Optional[Mapping[int, list[Criterio]]] = None,
) -> TaskOut:
    arestas = list(arestas)
    saida = TaskOut.model_validate(task)
    saida.depende_de = grafo.depende_de(arestas, task.id)
    saida.travando = grafo.travando(arestas, task.id)
    saida.bloqueada = grafo.bloqueada(arestas, task.id, concluidas)
    saida.criterios = [
        CriterioOut.model_validate(c) for c in (criterios or {}).get(task.id, [])
    ]
    return saida


def montar_tasks(
    tasks: Iterable[Task],
    arestas: Iterable[tuple[int, int]],
    concluidas: set[int],
    criterios: Optional[Mapping[int, list[Criterio]]] = None,
) -> list[TaskOut]:
    # As arestas sao materializadas uma vez: `montar_task` percorre a lista
    # inteira por task, e um gerador se esgotaria na primeira.
    arestas = list(arestas)
    return [montar_task(t, arestas, concluidas, criterios) for t in tasks]
