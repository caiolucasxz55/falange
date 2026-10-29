"""evidencia da conclusao + criterio.evidencia_id + autonomia de concluir

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-29

A virada da V2: uma task concluida pela IA passa a precisar de prova. A
tabela guarda a prova, `criterio.evidencia_id` liga cada criterio a sua, e
`dominio/conclusao.py` decide.

O valor novo do enum `tipo_acao` precisa sair da transacao da migration:
Postgres recusa usar um valor de enum adicionado na mesma transacao, e o
INSERT em `autonomia` logo abaixo usa exatamente esse valor. Dai o
`autocommit_block`.

O downgrade nao desfaz o valor do enum, porque o Postgres nao remove valor
de enum -- nao existe `ALTER TYPE ... DROP VALUE`. Ele apaga as linhas de
autonomia e as tabelas; `concluir_com_evidencia` fica no tipo, inerte. Esta
dito aqui para ninguem procurar o bug depois.
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

tipo_evidencia = sa.Enum(
    "commit", "teste", "link", "manual", name="tipo_evidencia"
)


def upgrade() -> None:
    tipo_evidencia.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "evidencia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("task.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tipo",
            # create_type=False: o tipo foi criado uma vez acima.
            sa.Enum(
                "commit",
                "teste",
                "link",
                "manual",
                name="tipo_evidencia",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "referencia", sa.String(500), nullable=False, server_default=""
        ),
        sa.Column("resumo", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "autor_id",
            sa.Integer(),
            sa.ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_evidencia_task_id", "evidencia", ["task_id"])
    op.create_index("ix_evidencia_autor_id", "evidencia", ["autor_id"])

    # SET NULL: apagar a prova nao apaga o criterio. Ele volta a "nao
    # verificado", que e a verdade depois de a prova sair.
    op.add_column(
        "criterio", sa.Column("evidencia_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "criterio_evidencia_id_fkey",
        "criterio",
        "evidencia",
        ["evidencia_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_criterio_evidencia_id", "criterio", ["evidencia_id"])

    # Fora da transacao: ver o docstring.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE tipo_acao ADD VALUE IF NOT EXISTS "
            "'concluir_com_evidencia'"
        )

    # Uma linha por projeto, em `perguntar`. Autonomia se conquista, nao se
    # herda -- e esta e a acao que mais pede desconfianca, porque e a IA
    # atestando o proprio trabalho.
    op.execute(
        "INSERT INTO autonomia (projeto_id, tipo_acao, nivel) "
        "SELECT id, 'concluir_com_evidencia', 'perguntar' FROM projeto"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM autonomia WHERE tipo_acao = 'concluir_com_evidencia'"
    )

    op.drop_index("ix_criterio_evidencia_id", table_name="criterio")
    op.drop_constraint("criterio_evidencia_id_fkey", "criterio", type_="foreignkey")
    op.drop_column("criterio", "evidencia_id")

    op.drop_index("ix_evidencia_autor_id", table_name="evidencia")
    op.drop_index("ix_evidencia_task_id", table_name="evidencia")
    op.drop_table("evidencia")
    tipo_evidencia.drop(op.get_bind(), checkfirst=True)
    # `concluir_com_evidencia` continua no enum tipo_acao: Postgres nao tem
    # DROP VALUE. Inerte, sem linha apontando para ele.
