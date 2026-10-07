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


def entrada_permitida(
    cabecalho: Optional[str], esperado: str, access_confere: bool
) -> bool:
    """A porta abre com o token compartilhado OU com um access token valido.

    Duas credenciais chegam pelo mesmo header `Authorization: Bearer`: o
    segredo compartilhado (MCP e proxy da tela) e o JWT de quem fez login.
    Conferir so o primeiro barraria todo usuario logado com 401 antes de a
    rota existir -- foi exatamente o que aconteceu na primeira versao disto.

    Aqui so se decide se ENTRA. Quem e a pessoa e o que ela pode fazer e
    assunto de `seguranca/dependencias.py`, que le a sessao e o papel no
    banco.
    """
    if not esperado:
        # Sem token configurado, a porta esta aberta de proposito (dev local).
        return True
    return token_valido(cabecalho, esperado) or access_confere


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


# Valor do header X-Falange-Fonte que o MCP manda em toda chamada.
#
# Serve para DUAS coisas, e so: derivar `origem` da task e reconhecer a
# conta de servico em `seguranca/dependencias.py`. Autorizacao nao passa
# mais por aqui -- quem decide e o papel, em `dominio/papeis.py`.
FONTE_MCP = "mcp"
