"""dependencia N:N, no lugar de task.bloqueada_por

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-20

Uma task passa a poder esperar por VARIAS. A coluna `bloqueada_por` so
cabia uma, entao vira tabela, e o que existia e copiado como uma aresta por
linha antes de a coluna sair.

O downgrade nao consegue ser fiel: com mais de uma dependencia por task,
nao ha onde guardar a segunda. Ele mantem a MENOR (id mais baixo) e descarta
o resto, o que e a unica reducao honesta -- e esta dito aqui para ninguem
descobrir isso perdendo dado.
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dependencia",
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("task.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "depende_de_id",
            sa.Integer(),
            sa.ForeignKey("task.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_dependencia_depende_de_id", "dependencia", ["depende_de_id"]
    )

    # Uma aresta por bloqueio existente. `IS NOT NULL` basta: a FK antiga era
    # ON DELETE SET NULL, entao nao ha ponteiro para id morto.
    op.execute(
        "INSERT INTO dependencia (task_id, depende_de_id) "
        "SELECT id, bloqueada_por FROM task WHERE bloqueada_por IS NOT NULL"
    )

    op.drop_column("task", "bloqueada_por")


def downgrade() -> None:
    op.add_column("task", sa.Column("bloqueada_por", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "task_bloqueada_por_fkey", "task", "task",
        ["bloqueada_por"], ["id"], ondelete="SET NULL",
    )
    # So a menor dependencia de cada task sobrevive: a coluna nao sabe
    # representar duas. Perda assumida e documentada.
    op.execute(
        "UPDATE task SET bloqueada_por = ("
        "  SELECT MIN(d.depende_de_id) FROM dependencia d WHERE d.task_id = task.id"
        ")"
    )
    op.drop_index("ix_dependencia_depende_de_id", table_name="dependencia")
    op.drop_table("dependencia")
