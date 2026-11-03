"""Caminho literal tem de ser declarado ANTES do parametrizado que o cobre.

O FastAPI casa na ORDEM DE DECLARACAO. Com `/tasks/{task_id}` antes de
`/tasks/contagem-por-bloco`, o literal nunca e alcancado: "contagem-por-bloco"
cai no parametro e vira 422 ao ser lido como int.

Isso ja esta escrito no `CLAUDE.md` e num comentario em `rotas/tasks.py`, e
mesmo assim e exatamente o tipo de coisa que volta -- basta alguem mover uma
rota de lugar, ou acrescentar uma nova no fim do arquivo. Comentario nao
impede reordenacao; este teste impede.

A varredura e no FONTE, nao no app montado: e a ordem no arquivo que
determina a ordem de registro, e le-la direto e o que torna a mensagem de
erro util ("mova X para antes de Y").
"""

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PASTA = RAIZ / "backend" / "rotas"

_DECORADOR = re.compile(
    r'^@rotas\.(get|post|patch|put|delete)\(\s*\n?\s*"([^"]+)"', re.M
)


def rotas_por_arquivo() -> dict[str, list[str]]:
    """Caminhos de cada arquivo, na ordem em que aparecem."""
    achadas: dict[str, list[str]] = {}
    for caminho in sorted(PASTA.glob("*.py")):
        texto = caminho.read_text(encoding="utf-8")
        encontradas = [m.group(2) for m in _DECORADOR.finditer(texto)]
        if encontradas:
            achadas[caminho.name] = encontradas
    return achadas


def cobre(parametrizado: str, literal: str) -> bool:
    """O caminho parametrizado casaria com o literal?

    Mesmo numero de segmentos, e cada segmento do parametrizado ou e um
    `{param}` ou e identico ao do literal.
    """
    a = parametrizado.strip("/").split("/")
    b = literal.strip("/").split("/")
    if len(a) != len(b):
        return False
    return all(
        pedaco.startswith("{") or pedaco == outro for pedaco, outro in zip(a, b)
    )


def test_a_varredura_acha_as_rotas():
    """Sem isto, um regex quebrado faria o teste abaixo passar vazio."""
    por_arquivo = rotas_por_arquivo()
    assert len(por_arquivo) >= 8, f"achou so {len(por_arquivo)} arquivos"

    todas = [c for lista in por_arquivo.values() for c in lista]
    assert "/tasks" in todas
    assert "/tasks/contagem-por-bloco" in todas
    assert "/marcos/previsao" in todas


def test_a_funcao_cobre_reconhece_o_caso_conhecido():
    """O proprio detector testado, com os dois casos que motivaram isto."""
    assert cobre("/tasks/{task_id}", "/tasks/contagem-por-bloco")
    assert cobre("/marcos/{marco_id}", "/marcos/previsao")
    # Nao cobre: numero de segmentos diferente.
    assert not cobre("/tasks/{task_id}", "/tasks/{task_id}/status")
    # Nao cobre: segmento literal diferente.
    assert not cobre("/tasks/{task_id}/status", "/tasks/{task_id}/bloqueio")


@pytest.mark.parametrize("arquivo", sorted(rotas_por_arquivo()), ids=str)
def test_literal_vem_antes_do_parametrizado_que_o_cobre(arquivo):
    caminhos = rotas_por_arquivo()[arquivo]

    for i, parametrizado in enumerate(caminhos):
        if "{" not in parametrizado:
            continue
        for j, literal in enumerate(caminhos):
            if j <= i or "{" in literal:
                continue
            assert not cobre(parametrizado, literal), (
                f"{arquivo}: '{literal}' e declarado DEPOIS de "
                f"'{parametrizado}', que o cobre. O FastAPI casa na ordem de "
                f"declaracao, entao '{literal}' nunca seria alcancado -- o "
                f"segmento literal cairia no parametro e viraria 422. "
                f"Mova '{literal}' para antes."
            )
