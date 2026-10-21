"""criterio de aceite em tabela, extraido das descricoes existentes

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-21

O criterio de aceite ja era obrigatorio -- mas como uma LINHA de texto
dentro da descricao, exigida pelo lint da pre-task. Servia para a pessoa
ler: nada no sistema sabia quantos criterios uma task tinha, nem quais
faltavam.

O upgrade copia o que da das descricoes (melhor esforco) e MANTEM o texto
onde esta. Nao e redundancia por descuido: a descricao e a prosa que a
pessoa escreveu, e reescreve-la para tirar a linha seria o upgrade editando
conteudo humano.

Limites do melhor esforco, por isso documentados aqui e nao descobertos
depois:

- task sem a linha (ou sem descricao) fica com ZERO criterio. O "de 1 a 5"
  vale para o que se CRIA daqui pra frente; nao ha como inventar criterio
  para task antiga.
- o criterio e tomado do marcador ate o fim da descricao, que e como as
  descricoes deste banco estao escritas. Linha de bullet logo abaixo do
  marcador vira um criterio por bullet.
- texto acima de 200 chars e cortado, com reticencia, porque a coluna tem
  limite de negocio e truncar visivelmente e melhor que recusar a migration.

`evidencia_id` NAO entra aqui. Ele so tem significado com a tabela
`evidencia`, da Fase F, e uma coluna apontando para o que nao existe nao
seria uma FK -- seria um inteiro solto esperando virar uma. Entra junto com
a tabela que ele referencia.
"""

import re
import unicodedata

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

MAX_TEXTO = 200
MAX_CRITERIOS = 5

# "Criterio de aceite", "Critério de aceite:", "criterios de aceite" -- o
# banco tem as tres formas, e o acento some na normalizacao.
_MARCADOR = re.compile(r"criterios?\s+de\s+aceite\s*:?\s*", re.I)
_BULLET = re.compile(r"^\s*[-*]\s+", re.M)


def _sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def extrair(descricao: str) -> list[str]:
    """Os criterios escondidos numa descricao. Lista vazia quando nao ha.

    A busca roda sobre o texto SEM acento, mas o corte usa os indices no
    texto original: NFKD preserva a contagem de caracteres para acento
    latino, entao as posicoes batem e o criterio sai como foi escrito.
    """
    if not descricao:
        return []

    sem_acento = _sem_acento(descricao)
    achado = _MARCADOR.search(sem_acento)
    if not achado or len(sem_acento) != len(descricao):
        return []

    resto = descricao[achado.end():].strip()
    if not resto:
        return []

    # Bullets logo abaixo do marcador: um criterio por bullet. Sem bullet, o
    # resto inteiro e um criterio so.
    if _BULLET.search(resto):
        brutos = [_BULLET.sub("", linha).strip() for linha in resto.splitlines()]
    else:
        brutos = [" ".join(resto.split())]

    criterios = []
    for bruto in brutos:
        if not bruto:
            continue
        criterios.append(bruto if len(bruto) <= MAX_TEXTO else bruto[:197] + "...")
    return criterios[:MAX_CRITERIOS]


def upgrade() -> None:
    op.create_table(
        "criterio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("task.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("cumprido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("task_id", "ordem", name="uq_criterio_task_ordem"),
    )
    op.create_index("ix_criterio_task_id", "criterio", ["task_id"])

    # A extracao e em Python, nao em SQL: a regra envolve acento, bullet e
    # truncagem, e a mesma funcao fica testavel fora da migration.
    conexao = op.get_bind()
    linhas = conexao.execute(
        sa.text("SELECT id, descricao FROM task WHERE descricao <> ''")
    ).fetchall()

    inserir = sa.text(
        "INSERT INTO criterio (task_id, texto, ordem) "
        "VALUES (:task_id, :texto, :ordem)"
    )
    for task_id, descricao in linhas:
        for ordem, texto in enumerate(extrair(descricao or "")):
            conexao.execute(
                inserir, {"task_id": task_id, "texto": texto, "ordem": ordem}
            )


def downgrade() -> None:
    # Sem perda: a descricao nunca foi alterada, entao o texto de onde cada
    # criterio saiu continua la.
    op.drop_index("ix_criterio_task_id", table_name="criterio")
    op.drop_table("criterio")
