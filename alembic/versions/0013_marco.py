"""marco, e task.marco_id

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-03

Da dado real a uma regra que ja estava escrita: a prioridade `alta` sempre
valeu para task que "e pre-requisito de uma entrega proxima", mas nada no
sistema sabia o que era uma entrega nem quando ela era.

`task.marco_id` e NULO por padrao e com `ON DELETE SET NULL`: apagar um
marco nao pode apagar trabalho. A task perde o agrupamento e continua.
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marco",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "projeto_id",
            sa.Integer(),
            sa.ForeignKey("projeto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(120), nullable=False),
        # Date, nao DateTime: prazo de entrega e um dia, nao um instante.
        sa.Column("data_alvo", sa.Date(), nullable=True),
        sa.Column("fechado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_marco_projeto_id", "marco", ["projeto_id"])

    op.add_column("task", sa.Column("marco_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "task_marco_id_fkey",
        "task",
        "marco",
        ["marco_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_task_marco_id", "task", ["marco_id"])


def downgrade() -> None:
    # Sem perda de trabalho: so o agrupamento some. As tasks ficam.
    op.drop_index("ix_task_marco_id", table_name="task")
    op.drop_constraint("task_marco_id_fkey", "task", type_="foreignkey")
    op.drop_column("task", "marco_id")

    op.drop_index("ix_marco_projeto_id", table_name="marco")
    op.drop_table("marco")
