"""Qual transporte este processo esta servindo.

Existe por causa de UMA tool: `coletar_evidencias` roda `git` na maquina
onde o servidor esta. No stdio isso e a maquina do dev, e o repositorio e o
dele. No SSE o servidor roda num container, longe de quem chamou -- rodar
git ali leria um repositorio que nao e o de ninguem, ou nenhum.

Por isso a tool recusa no SSE em vez de responder errado. Uma lista vazia
de commits pareceria "nao ha evidencia", que e exatamente a conclusao
oposta a verdade ("nao da para olhar daqui").

O entrypoint declara o transporte ao montar o servidor; nao e adivinhado
pelo nome nem por variavel de ambiente, para nao haver como ficar errado em
silencio.
"""

LOCAL = "stdio"
REMOTO = "sse"

# Default conservador: se alguem montar o servidor sem declarar, a tool que
# depende do disco recusa, em vez de ler o disco errado.
_atual = REMOTO


def definir(nome: str) -> None:
    if nome not in (LOCAL, REMOTO):
        raise ValueError(f"transporte '{nome}' desconhecido")
    global _atual
    _atual = nome


def atual() -> str:
    return _atual


def e_local() -> bool:
    return _atual == LOCAL
