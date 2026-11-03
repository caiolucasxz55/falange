"""Repasse de credencial do MCP: quem o backend acha que esta chamando.

O que estes testes prendem e a coisa que, errada, nao da erro nenhum: as
tools voltarem a falar com o backend como o SERVIDOR em vez de como a
pessoa. Isso nao quebra teste nem levanta excecao -- so faz `autor_id`,
papel e projeto ficarem de outra conta, em silencio.
"""

import asyncio

import pytest

from falange_mcp import credencial, transporte
from falange_mcp.server import _com_credencial, build_server

TOKEN = "flg_abcd1234_" + "s" * 43


@pytest.fixture(autouse=True)
def credencial_limpa():
    """Cada teste comeca sem credencial de chamador, e no stdio.

    Duas limpezas, as duas necessarias:

    - o ContextVar da credencial e de modulo, e um teste que deixasse valor
      sujo faria o seguinte passar por motivo errado;
    - o transporte tambem e de modulo, e o default dele e REMOTO (o lado
      conservador). Como `atual()` so cai no token do servidor no stdio,
      sem fixar isso os testes do fallback falhariam por motivo que nao e
      o deles.
    """
    handle = credencial.definir(None)
    transporte_anterior = transporte.atual()
    transporte.definir(transporte.LOCAL)
    yield
    transporte.definir(transporte_anterior)
    credencial.limpar(handle)


# ------------------------------------------------------ leitura do header


@pytest.mark.parametrize(
    "cabecalho,esperado",
    [
        (f"Bearer {TOKEN}", TOKEN),
        (f"Bearer   {TOKEN}  ", TOKEN),
        ("Bearer ", None),
        ("Basic abc", None),
        (TOKEN, None),  # sem o prefixo
        (None, None),
        ("", None),
    ],
)
def test_le_o_token_do_header(cabecalho, esperado):
    assert credencial.do_cabecalho(cabecalho) == esperado


# ------------------------------------------------------------- o formato


def test_reconhece_o_formato_do_token_de_conexao():
    assert credencial.partes_token(TOKEN) == ("abcd1234", "s" * 43)


@pytest.mark.parametrize(
    "lixo",
    [
        None,
        "",
        "flg",
        "flg_curto_x",
        "xxx_abcd1234_segredo",
        "flg_abcd1234_",
        # Um JWT nao pode passar pelo porteiro do SSE como token de conexao.
        "eyJhbGciOiJIUzI1NiJ9.corpo.assinatura",
    ],
)
def test_nao_confunde_outra_coisa_com_token_de_conexao(lixo):
    assert credencial.partes_token(lixo) is None


def test_o_formato_casa_com_o_do_backend():
    """O MCP nao importa de `backend/`, entao a constante e repetida la e ca.

    Se os dois divergirem, o sintoma e 401 na conexao -- nunca acesso
    indevido. Mesmo assim, divergir e bug, e este teste e o que avisa.
    """
    from backend.seguranca.token_mcp import MARCA, TAM_PREFIXO, gerar

    assert credencial.MARCA_CONEXAO == MARCA
    assert credencial.TAM_PREFIXO_CONEXAO == TAM_PREFIXO

    # E o gerador de verdade produz algo que o MCP reconhece.
    token, prefixo, _ = gerar()
    assert credencial.partes_token(token) == (prefixo, token.split("_", 2)[2])


# ----------------------------------------------------- qual token vai no ar


def test_sem_chamador_vale_o_token_do_servidor(monkeypatch):
    """O caso do stdio: o processo e do dev, e quem fala e a conta de servico."""
    monkeypatch.setattr(credencial.settings, "api_token", "token-do-servidor")
    assert credencial.atual() == "token-do-servidor"
    assert credencial.de_conexao() is False


def test_com_chamador_vale_o_token_dele(monkeypatch):
    monkeypatch.setattr(credencial.settings, "api_token", "token-do-servidor")
    handle = credencial.definir(TOKEN)
    try:
        assert credencial.atual() == TOKEN
        assert credencial.de_conexao() is True
    finally:
        credencial.limpar(handle)


def test_token_do_servidor_nao_contamina_a_proxima_chamada(monkeypatch):
    monkeypatch.setattr(credencial.settings, "api_token", "token-do-servidor")
    handle = credencial.definir(TOKEN)
    credencial.limpar(handle)
    # Depois do reset, a credencial do chamador anterior NAO pode sobrar:
    # a chamada seguinte agiria como outra pessoa.
    assert credencial.atual() == "token-do-servidor"
    assert credencial.de_conexao() is False


# -------------------------------------------------------------- o wrapper


class ContextoFalso:
    """O que o SDK injeta: um contexto com a requisicao HTTP do POST."""

    def __init__(self, cabecalhos=None, com_requisicao=True):
        self.request_context = type(
            "RC",
            (),
            {"request": type("Req", (), {"headers": cabecalhos or {}})()},
        )()
        if not com_requisicao:
            self.request_context = type("RC", (), {})()


def tool_falsa(a: int, b: str = "x") -> dict:
    """Docstring que a IA le."""
    return {"vista": credencial.atual(), "de_conexao": credencial.de_conexao()}


def test_wrapper_passa_a_credencial_do_contexto(monkeypatch):
    monkeypatch.setattr(credencial.settings, "api_token", "token-do-servidor")
    embrulhada = _com_credencial(tool_falsa)
    saida = embrulhada(1, ctx=ContextoFalso({"authorization": f"Bearer {TOKEN}"}))
    assert saida["vista"] == TOKEN
    assert saida["de_conexao"] is True


def test_wrapper_sem_contexto_cai_no_token_do_servidor(monkeypatch):
    """O stdio chama sem `ctx`: nao ha requisicao HTTP nenhuma."""
    monkeypatch.setattr(credencial.settings, "api_token", "token-do-servidor")
    assert _com_credencial(tool_falsa)(1)["vista"] == "token-do-servidor"


def test_wrapper_aguenta_contexto_sem_requisicao(monkeypatch):
    monkeypatch.setattr(credencial.settings, "api_token", "token-do-servidor")
    embrulhada = _com_credencial(tool_falsa)
    saida = embrulhada(1, ctx=ContextoFalso(com_requisicao=False))
    assert saida["vista"] == "token-do-servidor"


def test_wrapper_limpa_depois_mesmo_com_excecao(monkeypatch):
    monkeypatch.setattr(credencial.settings, "api_token", "token-do-servidor")

    def explode(_a: int) -> dict:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        _com_credencial(explode)(
            1, ctx=ContextoFalso({"authorization": f"Bearer {TOKEN}"})
        )
    # Sem o `finally`, a credencial daquela pessoa vazaria para a chamada
    # seguinte -- que agiria como ela.
    assert credencial.atual() == "token-do-servidor"


def test_wrapper_preserva_a_assinatura_que_a_ia_ve():
    import inspect

    embrulhada = _com_credencial(tool_falsa)
    assinatura = inspect.signature(embrulhada)
    assert list(assinatura.parameters) == ["a", "b", "ctx"]
    assert embrulhada.__doc__ == tool_falsa.__doc__
    assert embrulhada.__name__ == "tool_falsa"


def test_ctx_e_anotado_senao_vira_parametro_comum():
    """`functools.wraps` copia `__annotations__` da original, sem `ctx`.

    O SDK acha o parametro de contexto por `typing.get_type_hints`, nao
    pela assinatura. Sem reanotar, o `ctx` deixa de ser reconhecido como
    contexto, VAZA para o schema de toda tool e nunca e injetado -- foi
    exatamente o que aconteceu na primeira versao disto.
    """
    from mcp.server.mcpserver.utilities.context_injection import (
        find_context_parameter,
    )

    assert find_context_parameter(_com_credencial(tool_falsa)) == "ctx"


# -------------------------------------------------- o servidor de verdade


def test_nenhuma_tool_expoe_ctx_no_schema():
    """O guarda de regressao do bug acima, no servidor montado de verdade."""
    servidor = build_server("teste", transporte.LOCAL)
    ferramentas = asyncio.run(servidor.list_tools())
    assert len(ferramentas) >= 34

    vazaram = [
        f.name
        for f in ferramentas
        if "ctx" in ((f.input_schema or {}).get("properties") or {})
    ]
    assert vazaram == [], (
        "ctx vazou para o schema destas tools: a IA passaria a ver um "
        "parametro que e so de transporte, e o contexto nunca seria injetado"
    )


def test_as_tools_continuam_com_os_proprios_parametros():
    servidor = build_server("teste", transporte.LOCAL)
    ferramentas = {f.name: f for f in asyncio.run(servidor.list_tools())}

    criar = ferramentas["criar_task"].input_schema
    assert "titulo" in criar["properties"]
    assert "criterios" in criar["properties"]
    assert sorted(criar["required"]) == ["bloco", "estimativa", "titulo"]
    # A descricao e o que orienta a IA: o wrapper nao pode comer.
    assert "PP/P/M/G" in (ferramentas["criar_task"].description or "")


def test_no_sse_sem_credencial_nao_cai_na_conta_de_servico(monkeypatch):
    """O furo a uma linha de distancia, fechado por desenho.

    No SSE, cair no `API_TOKEN` significaria "nao sei quem esta chamando,
    entao vou falar como a conta de servico" -- que e o furo que esta fase
    veio fechar. O porteiro ja barra quem chega sem token, mas depender so
    dele deixaria a identidade compartilhada a um afrouxamento de
    distancia, sem erro nenhum aparecer.
    """
    monkeypatch.setattr(credencial.settings, "api_token", "token-do-servidor")

    anterior = transporte.atual()
    try:
        transporte.definir(transporte.REMOTO)
        assert credencial.atual() is None

        # Com credencial de chamador, o SSE funciona normalmente.
        handle = credencial.definir(TOKEN)
        try:
            assert credencial.atual() == TOKEN
        finally:
            credencial.limpar(handle)

        # E no stdio o fallback continua valendo: o processo e do dev.
        transporte.definir(transporte.LOCAL)
        assert credencial.atual() == "token-do-servidor"
    finally:
        transporte.definir(anterior)
