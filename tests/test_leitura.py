"""Testes da leitura de pasta do gerar_tasks_a_partir_de_arquivo.

Nao precisam de banco nem de backend: a checagem de duplicata (que iria na
rede) e substituida por uma lista vazia.
"""

import pytest

from falange_mcp import tools


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    """Aponta FALANGE_DOCS_ROOT para uma pasta temporaria e corta a rede."""
    monkeypatch.setattr(tools.settings, "falange_docs_root", str(tmp_path))
    monkeypatch.setattr(tools, "listar_tasks", lambda *a, **k: [])
    return tmp_path


def escrever(pasta, caminho_relativo, texto=""):
    destino = pasta / caminho_relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    return destino


def test_documentacao_vem_antes_do_codigo_e_em_ordem_alfabetica(raiz):
    escrever(raiz, "z_ultimo.py", "print('z')")
    escrever(raiz, "a_primeiro.py", "print('a')")
    escrever(raiz, "guia.md", "# Guia")
    escrever(raiz, "api.rst", "API")
    escrever(raiz, "notas.txt", "notas")

    saida = tools.gerar_tasks_a_partir_de_arquivo(".")

    assert saida["arquivos_lidos"] == [
        "api.rst",
        "guia.md",
        "notas.txt",
        "a_primeiro.py",
        "z_ultimo.py",
    ]
    # O cabecalho por arquivo entra no conteudo concatenado.
    assert "=== guia.md ===" in saida["conteudo"]


def test_pastas_ignoradas_nao_sao_lidas(raiz):
    escrever(raiz, "guia.md", "# Guia")
    escrever(raiz, "node_modules/lib/indice.js", "modulo")
    escrever(raiz, "src/__pycache__/cache.py", "cache")
    escrever(raiz, "src/app.py", "app")

    saida = tools.gerar_tasks_a_partir_de_arquivo(".")

    assert saida["arquivos_lidos"] == ["guia.md", "src/app.py"]
    ignoradas = {
        i["caminho"] for i in saida["arquivos_ignorados"] if i["motivo"] == "pasta ignorada"
    }
    assert ignoradas == {"node_modules/", "src/__pycache__/"}
    assert "modulo" not in saida["conteudo"]


def test_extensao_fora_da_lista_entra_como_ignorada(raiz):
    escrever(raiz, "guia.md", "# Guia")
    escrever(raiz, "logo.png", "binario")

    saida = tools.gerar_tasks_a_partir_de_arquivo(".")

    assert saida["arquivos_lidos"] == ["guia.md"]
    assert {"caminho": "logo.png", "motivo": "extensao"} in saida["arquivos_ignorados"]


def test_corte_no_limite_marca_o_que_ficou_de_fora(raiz, monkeypatch):
    monkeypatch.setattr(tools, "MAX_CHARS_PASTA", 200)
    escrever(raiz, "a.md", "a" * 150)
    escrever(raiz, "b.md", "b" * 150)
    escrever(raiz, "c.md", "c" * 150)

    saida = tools.gerar_tasks_a_partir_de_arquivo(".")

    assert saida["arquivos_lidos"] == ["a.md"]
    assert len(saida["conteudo"]) <= 200
    assert saida["truncado"] is True
    fora = {i["caminho"] for i in saida["arquivos_ignorados"] if i["motivo"] == "limite"}
    assert fora == {"b.md", "c.md"}


def test_caminho_fora_da_raiz_e_recusado(raiz):
    escrever(raiz, "guia.md", "# Guia")

    assert "fora da raiz permitida" in tools.gerar_tasks_a_partir_de_arquivo("..")["erro"]
    assert (
        "fora da raiz permitida"
        in tools.gerar_tasks_a_partir_de_arquivo("../../etc")["erro"]
    )


def test_arquivo_unico_nao_ganha_as_chaves_novas(raiz):
    escrever(raiz, "guia.md", "# Guia\nCriterio de aceite: nada muda aqui.")

    saida = tools.gerar_tasks_a_partir_de_arquivo("guia.md")

    assert "arquivos_lidos" not in saida
    assert "arquivos_ignorados" not in saida
    assert saida["conteudo"].startswith("# Guia")


def test_arquivo_unico_reporta_o_tamanho_inteiro_mesmo_truncado(raiz, monkeypatch):
    monkeypatch.setattr(tools, "MAX_CHARS", 50)
    escrever(raiz, "grande.md", "x" * 500)

    saida = tools.gerar_tasks_a_partir_de_arquivo("grande.md")

    assert saida["tamanho_chars"] == 500
    assert len(saida["conteudo"]) == 50
    assert saida["truncado"] is True
