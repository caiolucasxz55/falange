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
    cabecalho: Optional[str],
    esperado: str,
    access_confere: bool,
    parece_token_mcp: bool = False,
) -> bool:
    """A porta abre com o token compartilhado, um access token valido, ou um
    token de conexao do MCP com o nosso formato.

    TRES credenciais chegam pelo mesmo header `Authorization: Bearer`: o
    segredo compartilhado (MCP e proxy da tela), o JWT de quem fez login, e
    o token de conexao (`flg_...`) de quem ligou a IA pela tela. Conferir so
    o primeiro barraria os outros dois com 401 antes de a rota existir --
    foi exatamente o que aconteceu na primeira versao disto, com o JWT.

    `parece_token_mcp` e so o FORMATO, e nao podia ser mais que isso: o
    middleware nao tem sessao de banco para conferir o hash. Isso e seguro
    porque toda rota que faz algo depende de `obter_chamador`, que resolve o
    token de verdade e levanta 401 se ele nao presta. As unicas rotas sem
    `obter_chamador` sao `/health`, o login e o renovar -- e as duas ultimas
    autenticam por conta propria, com senha ou refresh. Ou seja: passar
    daqui com um token inventado nao alcanca nada.

    Aqui so se decide se ENTRA. Quem e a pessoa e o que ela pode fazer e
    assunto de `seguranca/dependencias.py`, que le a credencial e o papel no
    banco.
    """
    if not esperado:
        # Sem token configurado, a porta esta aberta de proposito (dev local).
        return True
    return token_valido(cabecalho, esperado) or access_confere or parece_token_mcp


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
