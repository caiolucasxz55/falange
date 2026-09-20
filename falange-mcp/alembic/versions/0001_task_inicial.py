"""schema inicial: tabela task

Revision ID: 0001
Revises:
Create Date: 2026-09-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

estimativa = sa.Enum("PP", "P", "M", "G", name="estimativa")
bloco = sa.Enum("frontend", "backend", "infra", "seguranca", name="bloco")
status = sa.Enum("aberta", "em_andamento", "concluida", name="status")


def upgrade() -> None:
    op.create_table(
        "task",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("titulo", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False, server_default=""),
        sa.Column("estimativa", estimativa, nullable=False),
        sa.Column("bloco", bloco, nullable=False),
        sa.Column("responsavel", sa.String(length=80), nullable=True),
        sa.Column(
            "bloqueada_por",
            sa.Integer(),
            sa.ForeignKey("task.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", status, nullable=False, server_default="aberta"),
    )
    # Os filtros de listagem e de carga batem nessas colunas.
    op.create_index("ix_task_bloco", "task", ["bloco"])
    op.create_index("ix_task_status", "task", ["status"])
    op.create_index("ix_task_responsavel", "task", ["responsavel"])


def downgrade() -> None:
    op.drop_index("ix_task_responsavel", table_name="task")
    op.drop_index("ix_task_status", table_name="task")
    op.drop_index("ix_task_bloco", table_name="task")
    op.drop_table("task")
    for enum in (estimativa, bloco, status):
        enum.drop(op.get_bind(), checkfirst=True)
