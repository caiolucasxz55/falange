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
PASTAS = ("backend", "falange_mcp", "tests")

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
