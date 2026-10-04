"""tabela configuracao

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuracao",
        sa.Column("chave", sa.String(length=60), primary_key=True),
        sa.Column("valor", sa.String(length=200), nullable=False),
        sa.Column(
            "atualizada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # Padrao: a IA pergunta antes de decidir. Quem quiser autonomia desliga.
    op.execute(
        "INSERT INTO configuracao (chave, valor) VALUES ('perguntas_ativas', 'true')"
    )


def downgrade() -> None:
    op.drop_table("configuracao")
