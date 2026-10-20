"""Cria um projeto se ele ainda nao existir. Idempotente.

A migration cria so o projeto `padrao`. O ambiente de teste precisa de um
segundo (`sandbox`), e cria-lo a mao a cada subida derrotaria o proposito de
um banco que se zera sozinho.

Uso:

    python scripts/semear_projeto.py <slug> [nome]

Nao e parte do app: roda uma vez, na subida, e sai. Por isso mora em
`scripts/` e nao em `backend/`.
"""

import asyncio
import sys

from backend.db import SessionLocal
from backend.models import Projeto
from backend.repositorio import projetos as repo


async def semear(slug: str, nome: str) -> None:
    # SessionLocal, e nao AsyncSession(engine): e a fabrica configurada do
    # app (expire_on_commit=False), que e o que o `refresh` do repositorio
    # espera.
    async with SessionLocal() as session:
        existente = await repo.buscar_por_slug(session, slug)
        if existente is not None:
            print(f"projeto '{slug}' ja existe (id {existente.id})")
            return
        criado: Projeto = await repo.criar(session, {"slug": slug, "nome": nome})
        print(f"projeto '{criado.slug}' criado (id {criado.id})")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    slug = sys.argv[1]
    nome = sys.argv[2] if len(sys.argv) > 2 else slug.capitalize()
    asyncio.run(semear(slug, nome))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
