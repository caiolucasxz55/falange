"""Com que credencial o backend e chamado NESTA chamada de tool.

Antes disto, as tools mandavam sempre o `API_TOKEN` do servidor. No stdio
isso e certo: o processo e do dev, e a conta de servico `falange-ia` e
quem fala. No SSE era um furo -- quem passava pelo porteiro agia com as
credenciais DO SERVIDOR, entao duas pessoas conectadas eram a MESMA conta
para o backend, e `autor_id`, papel e projeto saiam todos errados.

Agora cada chamada carrega a credencial de quem chamou.

## Por que ContextVar, e por que ela e preenchida tarde

A primeira ideia obvia -- um middleware ASGI que le o header e guarda num
ContextVar -- NAO funciona no SSE, e vale saber por que antes de alguem
tentar "simplificar" para isso:

o POST `/messages/` nao executa a tool. Ele valida, empurra a mensagem
para um stream de memoria e responde 202. Quem executa e a task de longa
duracao do `GET /sse`, que e outro contexto async -- e ContextVar nao
atravessa task criada por fora. O valor guardado no POST chegaria vazio na
tool.

O que o SDK FAZ carregar e o `Request` do POST, anexado a mensagem
(`ServerMessageMetadata(request_context=request)`). Entao a credencial e
extraida no unico ponto que ve as duas coisas: o wrapper de tool em
`server.py`, que recebe o `Context` da chamada e preenche este ContextVar
em volta da funcao.

O ContextVar continua sendo o jeito de nao ter que passar a credencial por
34 assinaturas de tool.
"""

import contextvars
from typing import Optional

from falange_mcp import transporte
from falange_mcp.config import settings

# Espelham `backend/seguranca/token_mcp.py`. O MCP nao importa nada de
# `backend/` -- mesma razao por que `template.py` repete os enums.
#
# Usados so para reconhecer o FORMATO: escolher a mensagem de erro certa e
# barrar na porta do SSE quem nem trouxe um token. Validar e do backend,
# que tem o banco. Se divergirem, o sintoma e 401 na conexao, nao acesso
# indevido -- o lado conservador do erro.
MARCA_CONEXAO = "flg"
TAM_PREFIXO_CONEXAO = 8

# Vazia = ninguem preencheu nesta chamada, e ai vale o token do servidor.
_atual: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "credencial_do_chamador", default=None
)


def definir(token: Optional[str]):
    """Fixa a credencial desta chamada. Devolve o handle para `reset`."""
    return _atual.set(token or None)


def limpar(handle) -> None:
    _atual.reset(handle)


def atual() -> Optional[str]:
    """O token que vai no `Authorization` desta chamada.

    A credencial de quem chamou, se houver. Sem ela, o `API_TOKEN` do
    servidor -- **mas so no stdio**.

    O fallback e proibido no SSE de proposito, e isso e desenho, nao
    paranoia: ali ele significaria "nao sei quem esta chamando, entao vou
    falar como a conta de servico", que e exatamente o furo que esta fase
    veio fechar. O porteiro do SSE ja barra quem chega sem token, mas
    depender so dele deixaria o furo a uma linha de distancia -- bastaria
    alguem afrouxar o porteiro no futuro para a identidade voltar a ser
    compartilhada, sem erro nenhum aparecer.

    Sem credencial no SSE, a tool chama o backend sem `Authorization` e
    leva 401. Barulhento, e e o que se quer.
    """
    do_chamador = _atual.get()
    if do_chamador:
        return do_chamador
    if transporte.e_local():
        return settings.api_token or None
    return None


def partes_token(token: Optional[str]) -> Optional[tuple[str, str]]:
    """`(prefixo, segredo)` se o token tem a cara de um token de conexao.

    So o formato. Espelha `partes()` do backend, e e o que o porteiro do
    SSE usa para recusar na conexao quem nem trouxe credencial.
    """
    if not token:
        return None
    pedacos = token.split("_", 2)
    if len(pedacos) != 3:
        return None
    marca, prefixo, segredo = pedacos
    if (
        marca != MARCA_CONEXAO
        or len(prefixo) != TAM_PREFIXO_CONEXAO
        or not segredo
    ):
        return None
    return prefixo, segredo


def de_conexao() -> bool:
    """Esta chamada esta usando um token de conexao de alguem?

    Serve para a mensagem de erro falar com a pessoa certa: quem conectou
    com token proprio nao tem `API_TOKEN` para conferir.
    """
    atual_token = _atual.get()
    return bool(atual_token and atual_token.startswith(f"{MARCA_CONEXAO}_"))


def do_cabecalho(authorization: Optional[str]) -> Optional[str]:
    """O token cru de um header `Authorization: Bearer <x>`.

    Devolve None para qualquer outra coisa. Nao julga o conteudo: quem
    decide se o token presta e o backend, que tem o banco.
    """
    if not authorization:
        return None
    prefixo = "Bearer "
    if not authorization.startswith(prefixo):
        return None
    return authorization[len(prefixo) :].strip() or None
