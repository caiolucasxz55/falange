"""usuario, sessao e as FKs de autoria

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-07

Cria a identidade por pessoa e liga autor/responsavel a ela.

As colunas de texto (`task.responsavel`, `nota.autor`) ficam: elas passam a
ser o rotulo de quem nunca virou conta, e o `_id` e a verdade quando existe.
O backfill liga o que casa por nome, sem inventar usuario para nome solto --
criar conta no lugar de alguem seria pior que nao ligar.

Semeia `falange-ia`, a conta de servico que o MCP usa. Sem senha: ela entra
pelo token compartilhado, nunca por login.
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

papel = sa.Enum("admin", "lead", "dev", "leitor", "ia", name="papel")

# create_type=False na COLUNA: o tipo e criado uma vez por `papel.create`,
# e sem isto o `create_table` tenta criar de novo e estoura com
# "type papel already exists". Mesmo padrao das migrations 0005 e 0006.
papel_coluna = sa.Enum(
    "admin", "lead", "dev", "leitor", "ia", name="papel", create_type=False
)

EMAIL_IA = "falange-ia@falange.local"


def upgrade() -> None:
    papel.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("senha_hash", sa.String(300), nullable=True),
        sa.Column("papel", papel_coluna, nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("email", name="uq_usuario_email"),
    )
    op.create_index("ix_usuario_email", "usuario", ["email"])

    op.create_table(
        "sessao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("usuario.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_hash", sa.String(64), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("usada_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("refresh_hash", name="uq_sessao_refresh_hash"),
    )
    op.create_index("ix_sessao_usuario_id", "sessao", ["usuario_id"])
    op.create_index("ix_sessao_refresh_hash", "sessao", ["refresh_hash"])

    # Conta de servico do MCP. Sem senha: `senha_hash` nulo faz o login
    # recusar sempre, entao a unica porta dela e o token compartilhado.
    op.execute(
        sa.text(
            "INSERT INTO usuario (email, nome, senha_hash, papel, ativo) "
            "VALUES (:email, 'Falange IA', NULL, 'ia', true)"
        ).bindparams(email=EMAIL_IA)
    )

    for tabela, coluna in (
        ("task", "autor_id"),
        ("task", "responsavel_id"),
        ("nota", "autor_id"),
        ("decisao", "autor_id"),
    ):
        op.add_column(
            tabela,
            sa.Column(
                coluna,
                sa.Integer(),
                sa.ForeignKey("usuario.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(f"ix_{tabela}_{coluna}", tabela, [coluna])

    # Backfill do que da para saber com certeza.
    #
    # Autoria da IA: `origem = 'ia'` ja era um fato gravado pelo backend a
    # partir do header, nao declarado pelo cliente, entao e seguro apontar
    # essas tasks para a conta de servico.
    op.execute(
        sa.text(
            "UPDATE task SET autor_id = (SELECT id FROM usuario WHERE email = :email) "
            "WHERE origem = 'ia'"
        ).bindparams(email=EMAIL_IA)
    )
    # Responsavel e autor por nome: so liga onde o texto casa com um usuario
    # existente. Hoje so existe a conta de servico, entao na pratica isto
    # nao liga nada -- fica para quando as contas do time forem criadas e a
    # migration rodar em outro banco.
    op.execute(
        "UPDATE task SET responsavel_id = u.id FROM usuario u "
        "WHERE lower(task.responsavel) = lower(u.nome) AND u.papel <> 'ia'"
    )
    op.execute(
        "UPDATE nota SET autor_id = u.id FROM usuario u "
        "WHERE lower(nota.autor) = lower(u.nome) AND u.papel <> 'ia'"
    )


def downgrade() -> None:
    for tabela, coluna in (
        ("decisao", "autor_id"),
        ("nota", "autor_id"),
        ("task", "responsavel_id"),
        ("task", "autor_id"),
    ):
        op.drop_index(f"ix_{tabela}_{coluna}", table_name=tabela)
        op.drop_column(tabela, coluna)

    op.drop_index("ix_sessao_refresh_hash", table_name="sessao")
    op.drop_index("ix_sessao_usuario_id", table_name="sessao")
    op.drop_table("sessao")

    op.drop_index("ix_usuario_email", table_name="usuario")
    op.drop_table("usuario")

    papel.drop(op.get_bind(), checkfirst=True)
