"""tabela nota

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nota",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("autor", sa.String(length=80), nullable=True),
        # A nota sobrevive a task: SET NULL em vez de CASCADE.
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("task.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "resolvida", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # A listagem filtra por essas duas colunas.
    op.create_index("ix_nota_resolvida", "nota", ["resolvida"])
    op.create_index("ix_nota_task_id", "nota", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_nota_task_id", table_name="nota")
    op.drop_index("ix_nota_resolvida", table_name="nota")
    op.drop_table("nota")
