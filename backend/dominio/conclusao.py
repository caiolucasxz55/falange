"""Quem pode dar uma task por concluida, e sob que prova.

Modulo puro. Nao abre sessao, nao faz HTTP, nao sabe de papel que nao
esteja no argumento.

A regra que da nome a fase: **uma task concluida pela IA precisa de prova,
nao de afirmacao**. A IA nao fecha task dizendo que fechou -- cada criterio
de aceite tem de estar ligado a uma evidencia (um commit, um teste, um
link, uma nota manual de um humano).

O humano conclui sem evidencia. Nao e privilegio por hierarquia: e que a
pessoa responde pelo que afirma, e travar o dev atras de um formulario faria
o Falange atrapalhar o trabalho em vez de organiza-lo. O preco e a
transparencia -- a task fica marcada como concluida sem evidencia, e isso
aparece no card.
"""

from typing import Any, Iterable, Optional

PAPEL_IA = "ia"


def _evidencia_de(criterio: Any) -> Optional[int]:
    """`evidencia_id` venha o criterio como dict ou como linha do banco."""
    if isinstance(criterio, dict):
        return criterio.get("evidencia_id")
    return getattr(criterio, "evidencia_id", None)


def criterios_sem_prova(criterios: Iterable[Any]) -> list[int]:
    """Ordem dos criterios que ainda nao tem evidencia ligada.

    Devolve `ordem` (1-based, como a pessoa le no card), nao id: a mensagem
    de erro e para alguem que esta olhando a lista, nao o banco.
    """
    faltando = []
    for posicao, criterio in enumerate(criterios, start=1):
        if _evidencia_de(criterio) is None:
            faltando.append(posicao)
    return faltando


def pode_concluir(papel: str, criterios: Iterable[Any]) -> tuple[bool, str]:
    """`(pode, motivo)`. O motivo e vazio quando pode.

    Para a IA, "todos os criterios com evidencia" nao basta: a task precisa
    TER criterio. Sem essa segunda metade a regra se burla sozinha --
    criar a task sem criterio nenhum satisfaria "todos" por vacuidade, e a
    exigencia de prova viraria opcional a escolha de quem deveria obedece-la.
    """
    criterios = list(criterios)

    if papel != PAPEL_IA:
        return True, ""

    if not criterios:
        return False, (
            "a IA nao conclui task sem criterio de aceite: sem criterio nao "
            "ha o que provar. Escreva os criterios (ou peca a um humano para "
            "concluir)"
        )

    faltando = criterios_sem_prova(criterios)
    if faltando:
        quais = ", ".join(f"#{n}" for n in faltando)
        return False, (
            f"criterio {quais} sem evidencia: a IA so conclui com prova em "
            "TODOS os criterios. Use registrar_evidencia antes de concluir"
        )

    return True, ""


def concluida_sem_evidencia(criterios: Iterable[Any]) -> bool:
    """A task foi fechada sem prova em algum criterio?

    Nao e erro: e o que o humano pode fazer e a IA nao. Existe para a tela
    poder dizer isso no card, em vez de o fato ficar so implicito na
    ausencia de linhas na tabela de evidencia.

    Task sem criterio nenhum tambem conta: nao ha prova de nada.
    """
    criterios = list(criterios)
    if not criterios:
        return True
    return bool(criterios_sem_prova(criterios))
