"""Testes das conversoes de valor das tools. Nao tocam no backend."""

from falange_mcp import tools
from falange_mcp.template import BLOCOS, ESTIMATIVAS, PRIORIDADES
from falange_mcp.tools import _canonizar, _checar


def test_canonizar_aceita_acento_e_caixa():
    assert _canonizar("segurança", BLOCOS) == "seguranca"
    assert _canonizar("SEGURANCA", BLOCOS) == "seguranca"
    assert _canonizar(" Infra ", BLOCOS) == "infra"
    assert _canonizar("média", PRIORIDADES) == "media"
    assert _canonizar("p", ESTIMATIVAS) == "P"


def test_canonizar_devolve_o_original_quando_nao_casa():
    # Assim a mensagem de erro cita o que a pessoa escreveu.
    assert _canonizar("mobile", BLOCOS) == "mobile"
    assert _canonizar(None, BLOCOS) is None


def test_mensagem_de_erro_concorda_em_genero():
    assert "prioridade 'urgente' invalida" in _checar("urgente", PRIORIDADES, "prioridade")
    assert "estimativa 'XG' invalida" in _checar("XG", ESTIMATIVAS, "estimativa")
    assert "bloco 'mobile' invalido" in _checar("mobile", BLOCOS, "bloco")


def test_bloqueada_false_sobrevive_a_montagem_dos_params(monkeypatch):
    """`False` e filtro, nao ausencia.

    Os outros filtros sao montados com `if v`, que descarta vazio. Jogar
    `bloqueada` no mesmo dict faria `bloqueada=False` -- "so o que da para
    pegar" -- virar "sem filtro", e a lista voltaria com tudo.
    """
    enviados = {}

    def espiao(metodo, caminho, params=None, **resto):
        enviados["params"] = params
        return []

    monkeypatch.setattr(tools, "_pedir", espiao)

    tools.listar_tasks(bloqueada=False)
    assert enviados["params"] == {"bloqueada": False}

    tools.listar_tasks(bloqueada=True, status="aberta")
    assert enviados["params"] == {"status": "aberta", "bloqueada": True}

    tools.listar_tasks()
    assert enviados["params"] is None
