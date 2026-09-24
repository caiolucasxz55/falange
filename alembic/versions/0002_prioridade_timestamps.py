"""prioridade e marcos de tempo na task

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

prioridade = sa.Enum("alta", "media", "baixa", name="prioridade")


def upgrade() -> None:
    # create_type=False no add_column: o tipo e criado uma vez aqui.
    prioridade.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "task",
        sa.Column(
            "prioridade",
            sa.Enum("alta", "media", "baixa", name="prioridade", create_type=False),
            nullable=False,
            server_default="media",
        ),
    )
    op.create_index("ix_task_prioridade", "task", ["prioridade"])

    # server_default now() tambem preenche as linhas que ja existem.
    op.add_column(
        "task",
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "task",
        sa.Column(
            "atualizada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "task", sa.Column("iniciada_em", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "task", sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("task", "concluida_em")
    op.drop_column("task", "iniciada_em")
    op.drop_column("task", "atualizada_em")
    op.drop_column("task", "criada_em")
    op.drop_index("ix_task_prioridade", table_name="task")
    op.drop_column("task", "prioridade")
    prioridade.drop(op.get_bind(), checkfirst=True)
