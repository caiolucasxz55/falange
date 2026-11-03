"""evento: o que aconteceu, quando e por quem

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-03

As outras tabelas guardam o estado ATUAL. Uma task diz que esta concluida;
nao diz quando saiu de aberta, quantas vezes voltou, nem quem a moveu. Essa
informacao existia e era jogada fora a cada escrita.

A tabela comeca VAZIA de proposito. Nao da para reconstruir historia que
nao foi guardada, e inventar eventos a partir dos timestamps atuais
produziria uma linha do tempo que parece real e nao e -- pior que comecar
do zero. `GET /evolucao` responde com o que houver, e com pouco tempo de
registro ele diz isso em vez de desenhar grafico de nada.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

tipo_evento = sa.Enum(
    "task_criada",
    "task_editada",
    "task_mudou_status",
    "task_apagada",
    "dependencia_adicionada",
    "dependencia_removida",
    "evidencia_registrada",
    "evidencia_apagada",
    "nota_criada",
    "nota_resolvida",
    "nota_apagada",
    name="tipo_evento",
)


def upgrade() -> None:
    tipo_evento.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "evento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "projeto_id",
            sa.Integer(),
            sa.ForeignKey("projeto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # SET NULL, nao CASCADE: "a task #12 foi apagada" e justamente o
        # evento que precisa sobreviver a task #12.
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("task.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tipo",
            sa.Enum(name="tipo_evento", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "autor_id",
            sa.Integer(),
            sa.ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "dados",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_evento_projeto_id", "evento", ["projeto_id"])
    op.create_index("ix_evento_task_id", "evento", ["task_id"])
    op.create_index("ix_evento_tipo", "evento", ["tipo"])
    op.create_index("ix_evento_autor_id", "evento", ["autor_id"])
    # Toda consulta daqui filtra por periodo; sem este indice, cada
    # pergunta varre a tabela que mais cresce no banco.
    op.create_index("ix_evento_criado_em", "evento", ["criado_em"])


def downgrade() -> None:
    for indice in (
        "ix_evento_criado_em",
        "ix_evento_autor_id",
        "ix_evento_tipo",
        "ix_evento_task_id",
        "ix_evento_projeto_id",
    ):
        op.drop_index(indice, table_name="evento")
    op.drop_table("evento")
    tipo_evento.drop(op.get_bind(), checkfirst=True)
