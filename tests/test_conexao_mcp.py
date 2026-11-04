"""A tela, o compose e o entrypoint tem de concordar sobre o endereco.

Este teste existe por causa de um bug de verdade, e ele e o exemplo mais
claro da classe inteira: o compose passou a subir Streamable HTTP
(`/mcp`), o painel "Conectar sua IA" continuou gerando um `.mcp.json`
apontando para `/sse`, e TODO MUNDO que seguisse a tela levava 404.

Nenhum teste pegou, e nao e por descuido de cobertura: cada lado estava
certo sozinho. O backend servia `/mcp` e o painel gerava JSON valido. O
que quebrou foi a JUNTA -- e junta entre um arquivo YAML, um modulo Python
e um componente TypeScript nao tem onde ser testada a nao ser aqui, lendo
os tres.

Por isso a varredura e textual. Nao da para importar um `.tsx` de dentro
do pytest, e montar um ambiente Node so para isto custaria mais do que
vale. Ler o texto e feio e funciona; o que importa e o erro aparecer no
`pytest`, e nao em producao.
"""

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent

COMPOSE = RAIZ / "docker-compose.yml"
PAINEL = RAIZ / "frontend" / "components" / "PainelConectarIA.tsx"
ENTRYPOINT = RAIZ / "falange_mcp" / "http.py"
EXEMPLO = RAIZ / ".mcp.example.json"


def texto(caminho: pathlib.Path) -> str:
    assert caminho.exists(), f"sumiu do repositorio: {caminho}"
    return caminho.read_text(encoding="utf-8")


def um(padrao: str, conteudo: str, onde: str) -> str:
    """O unico grupo que casa, ou falha dizendo o que procurava."""
    # MULTILINE porque alguns padroes ancoram em `^` para pegar a
    # constante de modulo, e nao uma mencao dela num comentario.
    achados = re.findall(padrao, conteudo, re.M)
    assert len(achados) == 1, (
        f"{onde}: esperava exatamente 1 ocorrencia de {padrao!r}, achei "
        f"{len(achados)}: {achados}"
    )
    return achados[0]


def test_o_compose_sobe_o_entrypoint_de_streamable_http():
    """Se isto mudar, os dois testes abaixo passam a cobrar outra coisa."""
    comando = um(
        r"command: python -m (falange_mcp\.\w+)", texto(COMPOSE), "docker-compose.yml"
    )
    assert comando == "falange_mcp.http", (
        f"o compose sobe {comando}, e este arquivo assume falange_mcp.http. "
        "Se a troca foi deliberada, ajuste o painel e o .mcp.example.json "
        "junto -- foi exatamente isso que ficou para tras da ultima vez."
    )


def test_o_caminho_do_painel_e_o_que_o_entrypoint_monta():
    do_painel = um(r'const CAMINHO_MCP = "([^"]+)"', texto(PAINEL), "PainelConectarIA")
    do_servidor = um(r'^CAMINHO = "([^"]+)"', texto(ENTRYPOINT), "falange_mcp/http.py")

    assert do_painel == do_servidor, (
        f"o painel manda a pessoa para '{do_painel}' e o servidor monta "
        f"'{do_servidor}'. Quem copiar o .mcp.json da tela leva 404."
    )


def test_a_porta_do_painel_e_a_que_o_compose_publica():
    do_painel = um(r"const PORTA_MCP = (\d+)", texto(PAINEL), "PainelConectarIA")
    publicadas = re.findall(r'"(\d+):(\d+)"', texto(COMPOSE))
    assert (do_painel, do_painel) in publicadas, (
        f"o painel aponta para a porta {do_painel}, que o compose nao "
        f"publica. Portas publicadas: {publicadas}"
    )


def test_o_tipo_no_mcp_json_casa_com_o_transporte():
    """`type` errado falha de um jeito confuso: o client nem tenta o caminho.

    `sse` e o transporte legado. Com o compose subindo Streamable HTTP, o
    tipo tem de ser `http`.
    """
    tipo = um(r'type: "(\w+)",', texto(PAINEL), "PainelConectarIA")
    assert tipo == "http", (
        f"o painel gera type: '{tipo}', mas o compose sobe Streamable HTTP"
    )


def test_o_exemplo_versionado_nao_tem_caminho_pessoal():
    """`.mcp.example.json` e copiado por quem clona: nada de /Users/fulano."""
    conteudo = texto(EXEMPLO)
    for suspeito in ("/Users/", "C:/Users", "c:/users", "\\Users\\"):
        assert suspeito not in conteudo, (
            f"'{suspeito}' no .mcp.example.json: caminho pessoal vazado"
        )


@pytest.mark.parametrize("arquivo", [PAINEL, EXEMPLO, COMPOSE], ids=lambda p: p.name)
def test_nenhum_token_de_conexao_vazou_para_arquivo_versionado(arquivo):
    """Um `flg_` de verdade aqui seria credencial no git.

    O painel monta o token em tempo de execucao, entao a string literal so
    apareceria se alguem tivesse colado um token real para testar.
    """
    achados = re.findall(r"flg_[A-Za-z0-9]{8}_[\w-]{20,}", texto(arquivo))
    assert not achados, f"token de conexao versionado em {arquivo.name}"
