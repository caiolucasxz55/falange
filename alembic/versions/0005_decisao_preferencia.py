"""origem da task, decisao e preferencia

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

origem = sa.Enum("ia", "humano", name="origem")
tipo_decisao = sa.Enum(
    "proxima_task",
    "prioridade",
    "estimativa",
    "quebrar_task",
    "pre_task",
    "ajuste_humano",
    name="tipo_decisao",
)
origem_preferencia = sa.Enum("explicita", "inferida", name="origem_preferencia")


def upgrade() -> None:
    origem.create(op.get_bind(), checkfirst=True)
    # Default humano: as tasks que ja existem nao viraram "da IA" por acidente.
    op.add_column(
        "task",
        sa.Column(
            "origem",
            sa.Enum("ia", "humano", name="origem", create_type=False),
            nullable=False,
            server_default="humano",
        ),
    )

    tipo_decisao.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "decisao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tipo",
            sa.Enum(
                "proxima_task",
                "prioridade",
                "estimativa",
                "quebrar_task",
                "pre_task",
                "ajuste_humano",
                name="tipo_decisao",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("sugerido", postgresql.JSONB(), nullable=False),
        sa.Column("escolhido", postgresql.JSONB(), nullable=False),
        sa.Column("aceita", sa.Boolean(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("responsavel", sa.String(length=80), nullable=True),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("task.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # A agregacao do perfil sempre filtra por tipo.
    op.create_index("ix_decisao_tipo", "decisao", ["tipo"])

    origem_preferencia.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "preferencia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("descricao", sa.String(length=200), nullable=False),
        sa.Column(
            "origem",
            sa.Enum(
                "explicita", "inferida", name="origem_preferencia", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("preferencia")
    origem_preferencia.drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_decisao_tipo", table_name="decisao")
    op.drop_table("decisao")
    tipo_decisao.drop(op.get_bind(), checkfirst=True)
    op.drop_column("task", "origem")
    origem.drop(op.get_bind(), checkfirst=True)
