"""Verificacao do token de acesso.

Modulo puro: recebe texto, devolve bool. Sem sessao, sem HTTP, sem framework.

Nao e autenticacao de usuario: e um segredo compartilhado que separa "quem
alcanca a porta" de "quem pode usar a API". Identidade por pessoa e multi
usuario sao V2, e sem elas nada aqui e atribuivel a ninguem.
"""

import secrets
from typing import Optional

PREFIXO = "Bearer "

# Caminhos que respondem sem token. So o healthcheck: o docker precisa dele
# antes de qualquer configuracao, e a resposta nao expoe dado de task.
CAMINHOS_LIVRES = frozenset({"/health"})


def token_valido(cabecalho: Optional[str], esperado: str) -> bool:
    """O header Authorization carrega o token certo?

    Comparacao em tempo constante: comparar com == vaza o tamanho do prefixo
    comum e permite adivinhar o segredo byte a byte.
    """
    if not esperado:
        # Sem token configurado, a porta esta aberta de proposito (dev local).
        return True
    if not cabecalho or not cabecalho.startswith(PREFIXO):
        return False
    return secrets.compare_digest(cabecalho[len(PREFIXO) :], esperado)


def exige_token(caminho: str, metodo: str, esperado: str) -> bool:
    """Esta requisicao precisa de token?

    OPTIONS fica de fora porque o preflight do navegador nao manda header
    nenhum: barrar ali quebraria o CORS sem ganhar seguranca, ja que o
    preflight nao le nem escreve dado.
    """
    if not esperado:
        return False
    if metodo == "OPTIONS":
        return False
    return caminho not in CAMINHOS_LIVRES
