"""Quem alcanca a API e o que cada lado pode fazer.

Pacote, e nao modulo, porque o V2 traz senha e sessao para ca. Hoje tem
so o token compartilhado, que diz "este cliente pode usar a API" e nunca
"quem e voce".
"""

from backend.seguranca.token import (
    CAMINHOS_LIVRES,
    FONTE_MCP,
    PREFIXO,
    entrada_permitida,
    exige_token,
    token_valido,
)

__all__ = [
    "CAMINHOS_LIVRES",
    "FONTE_MCP",
    "PREFIXO",
    "entrada_permitida",
    "exige_token",
    "token_valido",
]
