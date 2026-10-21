"""Guarda contra nome global inexistente usado dentro de funcao.

O import faltando so aparece quando a linha roda: `Origem.ia` no `criar_task`
derrubou todo `POST /tasks` com os 86 testes passando, porque nada aqui
cobre rota. Esta varredura e sintatica -- le o AST, nao executa nada -- e
pega exatamente essa classe de erro em todo modulo do projeto.

Insensivel a fluxo de proposito: um nome ligado em qualquer lugar do arquivo
conta como ligado. Prefere nao acusar a acusar errado.
"""

import ast
import builtins
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PASTAS = ("backend", "falange_mcp", "tests", "scripts")

# Globais que o Python injeta em todo modulo e que o AST nao mostra ligados.
INJETADOS = {"__file__", "__name__", "__doc__", "__package__"}


def modulos():
    return [c for p in PASTAS for c in sorted((RAIZ / p).rglob("*.py"))]


def nomes_livres(arvore: ast.AST) -> set[str]:
    usados: set[str] = set()
    ligados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Name):
            alvo = usados if isinstance(no.ctx, ast.Load) else ligados
            alvo.add(no.id)
        elif isinstance(no, ast.arg):
            ligados.add(no.arg)
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ligados.add(no.name)
        elif isinstance(no, ast.alias):
            ligados.add((no.asname or no.name).split(".")[0])
        elif isinstance(no, ast.ExceptHandler) and no.name:
            ligados.add(no.name)
        elif isinstance(no, ast.Global):
            ligados.update(no.names)
    return usados - ligados - set(dir(builtins)) - INJETADOS


@pytest.mark.parametrize("caminho", modulos(), ids=lambda c: c.name)
def test_modulo_nao_usa_nome_inexistente(caminho):
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))

    assert nomes_livres(arvore) == set()


def test_a_varredura_pega_um_import_faltando():
    # Sem esta guarda, a guarda poderia passar a nao pegar nada.
    arvore = ast.parse("def f():\n    return Origem.ia\n")

    assert nomes_livres(arvore) == {"Origem"}


# ---------------------------------------------------------------------------
# caractere de controle no fonte
# ---------------------------------------------------------------------------


# \t e \n sao legitimos; \r some no normalize do git. O resto nao tem o que
# fazer em codigo-fonte.
PERMITIDOS = {"\t", "\n", "\r"}


def fontes():
    """Os modulos varridos acima, mais as migrations.

    `alembic/` entra aqui e nao em PASTAS porque o guarda de nomes nao
    consegue ler migration (elas dependem de globais que o alembic injeta),
    mas o guarda de bytes consegue -- e migration tambem e escrita por
    script.
    """
    return modulos() + sorted((RAIZ / "alembic").rglob("*.py"))


@pytest.mark.parametrize("caminho", sorted(fontes()), ids=str)
def test_fonte_nao_tem_caractere_de_controle(caminho):
    """Um script com escaping errado grava 0x08 onde devia ir a sequencia \\b.

    Aconteceu de verdade, em `_VERBOS_OBSERVAVEIS` do template: 92
    caracteres 0x08 no lugar de `\\b`. Os regex compilavam, os testes de
    import passavam, e todo criterio de aceite era reprovado por "nao diz
    nada observavel" -- porque nenhum padrao casava com nada.

    E a pior classe de bug de edicao automatica: invisivel no diff, legal
    para o parser, e errado em silencio. Esta varredura e a unica coisa que
    olha para o byte.
    """
    texto = caminho.read_text(encoding="utf-8")
    achados = sorted(
        {c for c in texto if ord(c) < 32 and c not in PERMITIDOS}
    )
    assert not achados, (
        f"{caminho.relative_to(RAIZ)} tem caractere de controle "
        f"{[hex(ord(c)) for c in achados]}; provavelmente escaping comido "
        "por script de edicao"
    )
