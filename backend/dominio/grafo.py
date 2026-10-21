"""Grafo de dependencias entre tasks. Modulo puro: entra dado, sai dado.

Uma task pode depender de VARIAS, e nao de uma so. Isso muda o modelo de um
ponteiro (`bloqueada_por`) para um grafo dirigido -- e com grafo vem ciclo,
que precisa ser detectado antes de gravar.

A outra mudanca: "bloqueada" deixa de ser guardada e passa a ser DERIVADA
(tem dependencia nao concluida). Guardar o estado obrigava a limpar o
bloqueio ao concluir, e esquecer de limpar em algum caminho deixava task
"travada" por algo que ja acabou. Derivar nao pode ficar desatualizado.

As arestas chegam como `(task_id, depende_de_id)`: a task NAO anda enquanto
a outra nao terminar.
"""

from typing import Iterable, Optional


def _saida(arestas: Iterable[tuple[int, int]]) -> dict[int, set[int]]:
    """De quem cada task depende."""
    mapa: dict[int, set[int]] = {}
    for task_id, depende_de in arestas:
        mapa.setdefault(task_id, set()).add(depende_de)
    return mapa


def _entrada(arestas: Iterable[tuple[int, int]]) -> dict[int, set[int]]:
    """Quem depende de cada task -- quem ela esta travando."""
    mapa: dict[int, set[int]] = {}
    for task_id, depende_de in arestas:
        mapa.setdefault(depende_de, set()).add(task_id)
    return mapa


def depende_de(arestas: Iterable[tuple[int, int]], task_id: int) -> list[int]:
    """Dependencias diretas da task, ordenadas."""
    return sorted(_saida(arestas).get(task_id, set()))


def travando(arestas: Iterable[tuple[int, int]], task_id: int) -> list[int]:
    """Quem depende diretamente desta task."""
    return sorted(_entrada(arestas).get(task_id, set()))


def alcancaveis(
    arestas: Iterable[tuple[int, int]], inicio: int, reverso: bool = False
) -> set[int]:
    """Todas as tasks alcancaveis a partir de `inicio`, sem repeticao.

    `reverso=False` anda pelas dependencias (de quem `inicio` depende, de
    forma transitiva). `reverso=True` anda ao contrario: tudo que `inicio`
    trava, direta ou indiretamente.

    O conjunto de visitados nao e so otimizacao: sem ele, um ciclo ja
    gravado (ou um diamante) faria a busca nao terminar.
    """
    mapa = _entrada(arestas) if reverso else _saida(arestas)
    vistos: set[int] = set()
    pilha = [inicio]
    while pilha:
        atual = pilha.pop()
        for vizinho in mapa.get(atual, ()):
            if vizinho not in vistos:
                vistos.add(vizinho)
                pilha.append(vizinho)
    return vistos


def criaria_ciclo(
    arestas: Iterable[tuple[int, int]], task_id: int, depende_de_id: int
) -> bool:
    """Adicionar esta dependencia fecharia um ciclo?

    Fecha ciclo quando a candidata (`depende_de_id`) ja depende, direta ou
    transitivamente, da propria `task_id` -- ou quando sao a mesma task.
    """
    if task_id == depende_de_id:
        return True
    return task_id in alcancaveis(arestas, depende_de_id)


def bloqueada(
    arestas: Iterable[tuple[int, int]], task_id: int, concluidas: set[int]
) -> bool:
    """A task tem alguma dependencia DIRETA ainda nao concluida?

    So direta de proposito: se A depende de B e B depende de C, A fica
    bloqueada por B enquanto B nao acabar. Quando B acaba, A anda -- o
    estado de C ja esta refletido em B ter ou nao acabado.
    """
    return any(d not in concluidas for d in _saida(arestas).get(task_id, set()))


def destrava(
    arestas: Iterable[tuple[int, int]], task_id: int, concluidas: set[int]
) -> list[int]:
    """Quem passaria a andar se ESTA task fosse concluida agora.

    Alimenta o "destrava N tasks" da priorizacao. So conta quem ficaria
    livre de verdade: quem depende desta E nao tem outra pendencia.
    """
    livres = []
    saida = _saida(arestas)
    for candidata in _entrada(arestas).get(task_id, set()):
        outras = saida.get(candidata, set()) - {task_id}
        if all(d in concluidas for d in outras):
            livres.append(candidata)
    return sorted(livres)


def cadeia(
    arestas: Iterable[tuple[int, int]], task_id: int, concluidas: set[int]
) -> list[int]:
    """Tudo que ainda falta, transitivamente, para esta task andar.

    E o "o problema real esta em A" quando se olha para C.
    """
    return sorted(
        t for t in alcancaveis(arestas, task_id) if t not in concluidas
    )


def origem_da_cadeia(
    arestas: Iterable[tuple[int, int]], task_id: int, concluidas: set[int]
) -> Optional[int]:
    """A pendencia mais funda: a que nao depende de mais nada pendente.

    None quando a task nao esta esperando ninguem. Havendo empate, devolve
    o menor id -- estavel, para a tela nao trocar de resposta a cada
    atualizacao.
    """
    saida = _saida(arestas)
    pendentes = cadeia(arestas, task_id, concluidas)
    for candidata in pendentes:
        if all(d in concluidas for d in saida.get(candidata, set())):
            return candidata
    return None
