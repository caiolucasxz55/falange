"""Verificacao do token no lado do MCP.

Gemeo de `backend/seguranca.py`, duplicado de proposito: o MCP nao importa
nada de `backend/`. Sao seis linhas; acoplar os dois pacotes para economizar
isso custaria mais do que a repeticao. Mude os dois juntos.
"""

import secrets
from typing import Optional

PREFIXO = "Bearer "


def token_valido(cabecalho: Optional[str], esperado: str) -> bool:
    """Comparacao em tempo constante, para nao vazar o segredo byte a byte."""
    if not esperado:
        return True
    if not cabecalho or not cabecalho.startswith(PREFIXO):
        return False
    return secrets.compare_digest(cabecalho[len(PREFIXO) :], esperado)
