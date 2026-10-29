"""Contratos de entrada e saida do token de conexao do MCP."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.seguranca.token_mcp import MAX_NOME, MIN_NOME

# Teto de validade pedida. Um ano e muito; mais que isso e um token que
# ninguem vai lembrar de revogar.
MAX_DIAS = 365


class TokenMCPOut(BaseModel):
    """O token como ele aparece na lista. NUNCA carrega o segredo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    # O pedaco publico: serve para a pessoa reconhecer qual token e qual.
    prefixo: str
    projeto_id: int
    criado_em: datetime
    # Nulo = nunca usado. E o candidato obvio a revogar.
    ultimo_uso_em: Optional[datetime] = None
    expira_em: Optional[datetime] = None
    revogado_em: Optional[datetime] = None


class TokenMCPCriado(TokenMCPOut):
    """A resposta da CRIACAO, e a unica que carrega o segredo.

    Classe separada de proposito: assim nao ha como `token` escapar numa
    rota de listagem por descuido de reaproveitar o schema -- o campo
    simplesmente nao existe em `TokenMCPOut`.
    """

    token: str
    # Dito na resposta, e nao so na tela, porque quem consome a API direto
    # tambem precisa saber que nao ha segunda chance.
    aviso: str = (
        "guarde agora: o token nao volta a aparecer. Perdido, o caminho e "
        "revogar e criar outro"
    )


class TokenMCPNovo(BaseModel):
    nome: str = Field(min_length=MIN_NOME, max_length=MAX_NOME)
    # Dias de validade. Omitido, o token vale ate ser revogado.
    dias: Optional[int] = Field(default=None, ge=1, le=MAX_DIAS)

    @field_validator("nome")
    @classmethod
    def _aparar(cls, bruto: str) -> str:
        """Apara antes de medir, para nome de espacos nao passar do minimo."""
        limpo = bruto.strip()
        if len(limpo) < MIN_NOME:
            raise ValueError(
                f"de um nome ao token (pelo menos {MIN_NOME} chars): 'meu notebook'"
            )
        return limpo
