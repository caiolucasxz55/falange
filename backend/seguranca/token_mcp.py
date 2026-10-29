"""Token de conexao do MCP: a credencial que a pessoa cola no `.mcp.json`.

Modulo puro: entra texto, sai texto ou bool. Sem sessao, sem HTTP.

Existe porque, antes dele, ligar a IA no Falange exigia ter o repositorio
clonado -- e quem entrava pelo SSE usava as credenciais DO SERVIDOR, nao as
proprias. Com este token a pessoa conecta como ela mesma, de qualquer
maquina, e o `autor_id`, o papel e o projeto passam a ser os dela.

## Formato

    flg_<prefixo>_<segredo>

O `flg_` na frente e para scanner de segredo vazado reconhecer o que
encontrou (GitHub, gitleaks e afins casam por prefixo conhecido).

O **prefixo** fica no banco em CLARO, e e o que torna a validacao viavel:
sem ele, conferir um token exigiria testar o hash contra todas as linhas da
tabela. Com ele, e um SELECT por indice unico. Ele tambem e o que a tela
mostra na lista -- da para reconhecer qual token e qual sem revelar nenhum.

O **segredo** nunca e guardado: so o sha256 dele.

## Por que sha256 e nao argon2

Mesma razao do refresh em `seguranca/sessao.py`, e esta escrita la: o
segredo tem 256 bits de entropia, entao nao ha dicionario para percorrer
nem senha fraca para proteger. argon2 existe para encarecer o ataque a
segredo ADIVINHAVEL; aqui ele so custaria ~100ms a cada request, e este
token e conferido em TODA chamada do MCP, nao uma vez por login.
"""

import hashlib
import secrets
from typing import Optional

MARCA = "flg"
SEPARADOR = "_"

# Bytes antes do base64. O prefixo nao e segredo, so precisa ser unico; o
# segredo carrega a entropia toda.
BYTES_PREFIXO = 6
BYTES_SEGREDO = 32

# 6 bytes em base64 urlsafe dao 8 chars. Fixo, porque a coluna tem indice
# unico e a tela alinha a lista por ele.
TAM_PREFIXO = 8

# Rotulo que a pessoa da ao token ("meu notebook", "o CI").
MIN_NOME = 2
MAX_NOME = 60


def gerar() -> tuple[str, str, str]:
    """Devolve `(token_para_a_pessoa, prefixo, hash_do_segredo)`.

    O token completo so existe neste retorno. Depois daqui, o banco tem o
    prefixo e o hash, e mais nada -- se a pessoa perder o token, o caminho
    e revogar e gerar outro, nao recuperar.
    """
    prefixo = secrets.token_urlsafe(BYTES_PREFIXO)[:TAM_PREFIXO]
    segredo = secrets.token_urlsafe(BYTES_SEGREDO)
    token = f"{MARCA}{SEPARADOR}{prefixo}{SEPARADOR}{segredo}"
    return token, prefixo, hash_do_segredo(segredo)


def partes(token: Optional[str]) -> Optional[tuple[str, str]]:
    """`(prefixo, segredo)`, ou None se nao tem a cara de um token nosso.

    So separa; nao valida contra o banco. Serve para o porteiro decidir
    rapido "isto nem e um token MCP" e seguir tentando as outras
    credenciais, sem ir ao banco por nada.
    """
    if not token:
        return None
    pedacos = token.split(SEPARADOR, 2)
    if len(pedacos) != 3:
        return None
    marca, prefixo, segredo = pedacos
    if marca != MARCA or len(prefixo) != TAM_PREFIXO or not segredo:
        return None
    return prefixo, segredo


def hash_do_segredo(segredo: str) -> str:
    return hashlib.sha256(segredo.encode()).hexdigest()


def confere(segredo: str, guardado: Optional[str]) -> bool:
    """Comparacao em tempo constante, para nao vazar o prefixo comum."""
    if not guardado:
        return False
    return secrets.compare_digest(hash_do_segredo(segredo), guardado)


def nome_aceitavel(nome: str) -> Optional[str]:
    """None se serve; a razao em texto se nao serve."""
    limpo = (nome or "").strip()
    if len(limpo) < MIN_NOME:
        return f"de um nome ao token (pelo menos {MIN_NOME} chars): 'meu notebook'"
    if len(limpo) > MAX_NOME:
        return f"nome longo: no maximo {MAX_NOME} chars"
    return None
