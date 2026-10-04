"""tabela autonomia

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

tipo_acao = sa.Enum(
    "definir_prioridade",
    "definir_estimativa",
    "marcar_bloqueio",
    "criar_pre_tasks_aprovadas",
    name="tipo_acao",
)
nivel_autonomia = sa.Enum(
    "perguntar", "confirmar_em_lote", "automatico", name="nivel_autonomia"
)


def upgrade() -> None:
    tipo_acao.create(op.get_bind(), checkfirst=True)
    nivel_autonomia.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "autonomia",
        sa.Column(
            "tipo_acao",
            sa.Enum(
                "definir_prioridade",
                "definir_estimativa",
                "marcar_bloqueio",
                "criar_pre_tasks_aprovadas",
                name="tipo_acao",
                create_type=False,
            ),
            primary_key=True,
        ),
        sa.Column(
            "nivel",
            sa.Enum(
                "perguntar",
                "confirmar_em_lote",
                "automatico",
                name="nivel_autonomia",
                create_type=False,
            ),
            nullable=False,
            server_default="perguntar",
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # As quatro nascem em perguntar: autonomia se conquista, nao se herda.
    op.execute(
        "INSERT INTO autonomia (tipo_acao, nivel) VALUES "
        "('definir_prioridade', 'perguntar'), "
        "('definir_estimativa', 'perguntar'), "
        "('marcar_bloqueio', 'perguntar'), "
        "('criar_pre_tasks_aprovadas', 'perguntar')"
    )


def downgrade() -> None:
    op.drop_table("autonomia")
    nivel_autonomia.drop(op.get_bind(), checkfirst=True)
    tipo_acao.drop(op.get_bind(), checkfirst=True)
