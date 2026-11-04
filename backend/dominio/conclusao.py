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


def exige_prova(papel: str, via_mcp: bool = False) -> bool:
    """Esta conclusao precisa de evidencia?

    Duas formas de uma IA estar concluindo, e as DUAS contam:

    1. o papel e `ia` -- a conta de servico, que entra pelo token
       compartilhado (stdio local);
    2. a chamada veio pelo MCP -- uma pessoa ligou a IA dela com um token
       de conexao, e ali o papel resolvido e o DELA, humano.

    O caso 2 nao existia quando esta regra foi escrita, e abriu um buraco
    nela: a IA conectada pelo caminho remoto herdava o papel do dono e
    concluia task sem criterio e sem prova -- justamente o que a fase da
    evidencia veio impedir. Duas decisoes certas sozinhas que se
    contradiziam juntas.

    O header `X-Falange-Fonte: mcp` vai em TODA chamada do MCP, entao a
    informacao sempre esteve na requisicao; faltava olhar para ela.

    Sim, o header e do cliente e da para omitir. Mas isso nao e brecha: um
    humano que tira o header esta fazendo pela API o que ja pode fazer
    pela tela -- concluir sob a propria responsabilidade. O header aperta
    quando esta presente; ele nunca afrouxa nada.
    """
    return papel == PAPEL_IA or via_mcp


def pode_concluir(
    papel: str, criterios: Iterable[Any], via_mcp: bool = False
) -> tuple[bool, str]:
    """`(pode, motivo)`. O motivo e vazio quando pode.

    Para a IA, "todos os criterios com evidencia" nao basta: a task precisa
    TER criterio. Sem essa segunda metade a regra se burla sozinha --
    criar a task sem criterio nenhum satisfaria "todos" por vacuidade, e a
    exigencia de prova viraria opcional a escolha de quem deveria obedece-la.
    """
    criterios = list(criterios)

    if not exige_prova(papel, via_mcp):
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
