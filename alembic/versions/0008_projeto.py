"""projeto, e tudo o que existe passa a pertencer a um

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-20

Cria `projeto` e move o que ja existe para o projeto `padrao`.

A coluna entra NULLABLE, e preenchida e so entao vira NOT NULL. Criar
direto como NOT NULL falharia em qualquer banco com linha, que e o caso de
todos os que importam.

`configuracao` e `autonomia` trocam a chave primaria por uma composta: o
ajuste e a confianca valem POR projeto, entao a mesma chave pode existir em
dois projetos com valores diferentes.
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

SLUG_PADRAO = "padrao"

# Tabelas que ganham a coluna como FK comum (PK continua sendo `id`).
POR_PROJETO = ("task", "nota", "decisao", "preferencia")


def upgrade() -> None:
    op.create_table(
        "projeto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(40), nullable=False),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slug", name="uq_projeto_slug"),
    )
    op.create_index("ix_projeto_slug", "projeto", ["slug"])

    op.execute(
        sa.text("INSERT INTO projeto (slug, nome) VALUES (:slug, 'Padrao')")
        .bindparams(slug=SLUG_PADRAO)
    )
    padrao = (
        "(SELECT id FROM projeto WHERE slug = '" + SLUG_PADRAO + "')"
    )

    for tabela in POR_PROJETO:
        op.add_column(tabela, sa.Column("projeto_id", sa.Integer(), nullable=True))
        op.execute(f"UPDATE {tabela} SET projeto_id = {padrao}")
        op.alter_column(tabela, "projeto_id", nullable=False)
        op.create_foreign_key(
            f"fk_{tabela}_projeto", tabela, "projeto", ["projeto_id"], ["id"],
            ondelete="CASCADE",
        )
        op.create_index(f"ix_{tabela}_projeto_id", tabela, ["projeto_id"])

    # configuracao: a PK passa de (chave) para (projeto_id, chave).
    op.add_column("configuracao", sa.Column("projeto_id", sa.Integer(), nullable=True))
    op.execute(f"UPDATE configuracao SET projeto_id = {padrao}")
    op.alter_column("configuracao", "projeto_id", nullable=False)
    op.drop_constraint("configuracao_pkey", "configuracao", type_="primary")
    op.create_primary_key("configuracao_pkey", "configuracao", ["projeto_id", "chave"])
    op.create_foreign_key(
        "fk_configuracao_projeto", "configuracao", "projeto",
        ["projeto_id"], ["id"], ondelete="CASCADE",
    )

    # autonomia: a PK passa de (tipo_acao) para (projeto_id, tipo_acao).
    op.add_column("autonomia", sa.Column("projeto_id", sa.Integer(), nullable=True))
    op.execute(f"UPDATE autonomia SET projeto_id = {padrao}")
    op.alter_column("autonomia", "projeto_id", nullable=False)
    op.drop_constraint("autonomia_pkey", "autonomia", type_="primary")
    op.create_primary_key("autonomia_pkey", "autonomia", ["projeto_id", "tipo_acao"])
    op.create_foreign_key(
        "fk_autonomia_projeto", "autonomia", "projeto",
        ["projeto_id"], ["id"], ondelete="CASCADE",
    )


def downgrade() -> None:
    # Volta a chave simples. Se houver mais de um projeto, as linhas dos
    # outros colidiriam na PK antiga: apaga tudo o que nao e do padrao, que
    # e o unico desfazer honesto -- a estrutura antiga nao sabe representar.
    padrao = "(SELECT id FROM projeto WHERE slug = '" + SLUG_PADRAO + "')"
    op.execute(f"DELETE FROM configuracao WHERE projeto_id <> {padrao}")
    op.execute(f"DELETE FROM autonomia WHERE projeto_id <> {padrao}")
    for tabela in POR_PROJETO:
        op.execute(f"DELETE FROM {tabela} WHERE projeto_id <> {padrao}")

    op.drop_constraint("fk_autonomia_projeto", "autonomia", type_="foreignkey")
    op.drop_constraint("autonomia_pkey", "autonomia", type_="primary")
    op.create_primary_key("autonomia_pkey", "autonomia", ["tipo_acao"])
    op.drop_column("autonomia", "projeto_id")

    op.drop_constraint("fk_configuracao_projeto", "configuracao", type_="foreignkey")
    op.drop_constraint("configuracao_pkey", "configuracao", type_="primary")
    op.create_primary_key("configuracao_pkey", "configuracao", ["chave"])
    op.drop_column("configuracao", "projeto_id")

    for tabela in reversed(POR_PROJETO):
        op.drop_index(f"ix_{tabela}_projeto_id", table_name=tabela)
        op.drop_constraint(f"fk_{tabela}_projeto", tabela, type_="foreignkey")
        op.drop_column(tabela, "projeto_id")

    op.drop_index("ix_projeto_slug", table_name="projeto")
    op.drop_table("projeto")
