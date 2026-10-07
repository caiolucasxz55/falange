"""Limite de requisicoes por cliente.

Modulo puro: recebe o historico de horarios e devolve se passa. Quem guarda
o historico e o middleware.

Janela deslizante simples, em memoria. Nao e rate limit de producao: nao
sobrevive a reinicio e nao e compartilhado entre replicas. Serve para o que
foi pedido -- impedir que um script encha o banco em segundos.
"""

from typing import Optional

# Teto por cliente em uma janela. Generoso de proposito: a tela faz ~16
# requisicoes por minuto com polling, e o MCP trabalha em rajada.
MAX_POR_JANELA = 300
JANELA_SEGUNDOS = 60.0


def permitido(
    historico: list[float],
    agora: float,
    maximo: int = MAX_POR_JANELA,
    janela: float = JANELA_SEGUNDOS,
) -> tuple[bool, list[float]]:
    """A requisicao passa? Devolve (passa, historico ja podado).

    O historico volta sem os horarios que sairam da janela, para quem chama
    nao precisar limpar nada e a memoria nao crescer sem limite.
    """
    if maximo <= 0:
        # Zero ou negativo desliga o limite.
        return True, []

    recentes = [t for t in historico if agora - t < janela]
    if len(recentes) >= maximo:
        return False, recentes
    return True, [*recentes, agora]


def segundos_para_liberar(
    historico: list[float], agora: float, janela: float = JANELA_SEGUNDOS
) -> Optional[int]:
    """Quanto falta para a requisicao mais antiga sair da janela."""
    if not historico:
        return None
    return max(1, int(janela - (agora - min(historico))) + 1)
