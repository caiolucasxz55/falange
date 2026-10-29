"""token de conexao do MCP, um por maquina de cada pessoa

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-29

Abre o Falange para quem nao clonou o repositorio. Antes disto, ligar a IA
exigia o codigo em disco, e quem entrava pelo SSE usava as credenciais do
SERVIDOR -- duas pessoas no mesmo SSE eram a mesma conta para o backend.

Nao mexe em nada que existe: so cria a tabela. O token compartilhado
(`API_TOKEN`) e o JWT continuam valendo como antes, entao nenhum cliente
atual para de funcionar por causa desta migration.
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "token_mcp",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("usuario.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "projeto_id",
            sa.Integer(),
            sa.ForeignKey("projeto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(60), nullable=False),
        # Em claro e UNICO: e por ele que a validacao acha a linha. Sem o
        # indice, conferir um token seria hashear contra a tabela toda.
        sa.Column("prefixo", sa.String(8), nullable=False, unique=True),
        # sha256 hex tem 64 chars. Mesmo tamanho do refresh da sessao, e
        # pela mesma razao: segredo de 256 bits nao precisa de argon2.
        sa.Column("hash_segredo", sa.String(64), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ultimo_uso_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_token_mcp_usuario_id", "token_mcp", ["usuario_id"])
    op.create_index("ix_token_mcp_projeto_id", "token_mcp", ["projeto_id"])
    op.create_index("ix_token_mcp_prefixo", "token_mcp", ["prefixo"], unique=True)


def downgrade() -> None:
    # Sem perda de dado alheio: a tabela so tem token, e token revogado em
    # massa e o resultado correto de desfazer esta fase. Quem estava
    # conectado por token volta a precisar do token compartilhado.
    op.drop_index("ix_token_mcp_prefixo", table_name="token_mcp")
    op.drop_index("ix_token_mcp_projeto_id", table_name="token_mcp")
    op.drop_index("ix_token_mcp_usuario_id", table_name="token_mcp")
    op.drop_table("token_mcp")
