"""Token de conexao do MCP, um por maquina de cada pessoa.

Antes disto, conectar a IA ao Falange exigia o repositorio clonado, e quem
entrava pelo SSE usava as credenciais do SERVIDOR -- entao duas pessoas no
mesmo SSE eram a mesma conta para o backend. Esta tabela e o que faz a
identidade por pessoa da V2 sobreviver a porta do MCP.

O token carrega DOIS vinculos, e os dois importam:

- `usuario_id` diz quem e a pessoa. O papel dela continua lido do banco a
  cada request: o token nao congela permissao, so identifica.
- `projeto_id` diz onde ela escreve. Vem do token e nao de header porque
  quem conecta de fora nao tem um `.mcp.json` nosso para definir
  `FALANGE_PROJETO`, e cair no projeto `padrao` escreveria no lugar errado
  em silencio.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

# Primeiro model a importar de `seguranca/`, e de proposito:
# `seguranca/token_mcp.py` e o dono do FORMATO do token, e o tamanho do
# prefixo e parte do formato. E um modulo folha (nao importa models,
# repositorio nem rotas), entao nao ha ciclo -- e repetir o numero 8 aqui
# seria a duplicata que diverge.
from backend.seguranca.token_mcp import MAX_NOME, TAM_PREFIXO


class TokenMCP(Base):
    __tablename__ = "token_mcp"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), index=True
    )
    projeto_id: Mapped[int] = mapped_column(
        ForeignKey("projeto.id", ondelete="CASCADE"), index=True
    )

    # Rotulo de quem criou: quem tem tres tokens precisa saber qual revogar.
    nome: Mapped[str] = mapped_column(String(MAX_NOME))

    # Em CLARO, e com indice unico. E o que torna a validacao um SELECT em
    # vez de um hash contra a tabela toda -- e o que a tela mostra na lista
    # sem revelar segredo nenhum.
    prefixo: Mapped[str] = mapped_column(
        String(TAM_PREFIXO), unique=True, index=True
    )

    # So o sha256 do segredo. Um dump do banco nao vira acesso.
    hash_segredo: Mapped[str] = mapped_column(String(64))

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Nulo ate a primeira chamada. Serve para achar na tela o token que foi
    # gerado e esquecido -- o candidato obvio a revogar.
    ultimo_uso_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Nulo = vale ate revogar. Opcional de proposito: exigir prazo faria a
    # conexao da pessoa morrer sozinha no meio de uma sessao de trabalho.
    expira_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Preenchido ao revogar. A linha NAO e apagada, como na sessao: saber
    # que o token existiu e foi cortado vale mais que o espaco.
    revogado_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
