"""Junta a task guardada com o que o grafo deriva.

Mora em `rotas/` porque e montagem de resposta, nao dado nem regra: o
repositorio devolve linhas, o dominio calcula sobre arestas, e e aqui que
os dois viram um `TaskOut`.

Existe para `depende_de`, `travando`, `bloqueada`, `criterios` e
`concluida_sem_evidencia` sairem iguais em toda rota que devolve task. Montar isso a mao em cada uma era o
caminho curto para uma responder diferente da outra.
"""

from typing import Iterable, Mapping, Optional

from backend.dominio import conclusao, grafo
from backend.models import Criterio, Status, Task
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
    meus_criterios = (criterios or {}).get(task.id, [])
    saida.criterios = [CriterioOut.model_validate(c) for c in meus_criterios]
    # Calculado sempre, mas so significa algo em task concluida: numa task
    # aberta "sem evidencia" e o estado normal, nao uma informacao.
    saida.concluida_sem_evidencia = (
        task.status == Status.concluida
        and conclusao.concluida_sem_evidencia(meus_criterios)
    )
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
