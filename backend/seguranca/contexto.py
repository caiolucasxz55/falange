"""Quem esta chamando, acessivel sem passar por 20 assinaturas.

Existe por causa dos eventos. O repositorio escreve a linha de historia na
MESMA transacao da mudanca que ela descreve -- e o jeito de nao existir
mudanca sem evento. Mas o repositorio nao conhece o chamador, e levar
`autor_id` ate ele exigiria acrescentar o parametro em toda funcao de
escrita de task, dependencia, criterio, evidencia e nota, mais as rotas que
as chamam.

Um ContextVar preenchido por `obter_chamador` resolve isso sem espalhar o
assunto. Funciona porque o FastAPI atende cada request numa task propria, e
ContextVar e herdado pelas tasks filhas: o que a dependencia define, a rota
e o repositorio enxergam.

## O limite disto, dito aqui para nao virar atalho

So `autor_id` mora aqui, e so para registro. **Autorizacao nunca.**
Permissao passa por `Chamador.exigir()`, explicito na rota, porque uma
checagem de permissao escondida num contextvar e impossivel de auditar
lendo a rota -- e e a rota que alguem le para saber o que ela protege.

Valor ausente (None) e normal: tarefa de fundo, migration, teste. O evento
sai com `autor_id` nulo, que e a verdade, e nao um erro.
"""

import contextvars
from typing import Optional

_autor: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "autor_do_request", default=None
)


def definir_autor(usuario_id: Optional[int]):
    """Fixa o autor deste request. Devolve o handle para `limpar_autor`."""
    return _autor.set(usuario_id)


def limpar_autor(handle) -> None:
    _autor.reset(handle)


def autor_atual() -> Optional[int]:
    return _autor.get()
