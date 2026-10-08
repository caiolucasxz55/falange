"""Contratos de usuario e sessao.

`senha_hash` nao aparece em nenhum schema de saida. Nao e descuido: e o
unico jeito de garantir que ele nunca vaza por um endpoint novo que
reaproveite `UsuarioOut`.
"""

from datetime import datetime
from typing import Annotated, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from backend.models.usuario import Papel
from backend.schemas.limites import recusar_nulos
from backend.schemas.texto import NomeObrigatorio
from backend.seguranca.senha import MAX_SENHA, MIN_SENHA

# Checagem propria em vez de `EmailStr`: aquele tipo puxa a dependencia
# `email-validator`, e aqui o email e so um identificador de login unico --
# nao mandamos mensagem para ele. Formato grosseiro basta.
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=5,
        max_length=200,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nome: str
    papel: Papel
    ativo: bool
    criado_em: datetime


class UsuarioNovo(BaseModel):
    email: Email
    nome: NomeObrigatorio
    senha: str = Field(min_length=MIN_SENHA, max_length=MAX_SENHA)
    papel: Papel = Papel.dev


class UsuarioEdicao(BaseModel):
    """Edicao parcial. Papel e `ativo` cortam as sessoes vivas da pessoa."""

    nome: Optional[NomeObrigatorio] = None
    papel: Optional[Papel] = None
    ativo: Optional[bool] = None

    # Os tres sao NOT NULL na tabela: `{"papel": null}` chegava como None
    # e virava IntegrityError 500, driblando a guarda do ultimo admin.
    _sem_nulos = model_validator(mode="before")(
        recusar_nulos("nome", "papel", "ativo")
    )


class TrocaDeSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=MAX_SENHA)
    senha_nova: str = Field(min_length=MIN_SENHA, max_length=MAX_SENHA)


class Login(BaseModel):
    email: Email
    senha: str = Field(min_length=1, max_length=MAX_SENHA)


class Renovacao(BaseModel):
    refresh: str = Field(min_length=1, max_length=200)


class SessaoAberta(BaseModel):
    """O que o login devolve.

    O refresh sai aqui uma vez so, para quem chamou guardar. O backend nunca
    mostra de novo: ele guarda apenas o hash.
    """

    access: str
    refresh: str
    expira_em_minutos: int
    usuario: UsuarioOut


class Eu(BaseModel):
    """Quem a API acha que esta chamando, e o que ele alcanca.

    A tela usa `acoes` para nao desenhar botao que vai dar 403.
    """

    usuario: Optional[UsuarioOut]
    papel: Optional[Papel]
    acoes: list[str]
    # true quando nao ha login e a API esta tratando a chamada como admin
    # (EXIGIR_LOGIN=false). A tela avisa, em vez de parecer autenticada.
    sem_login: bool
