"""Testes da autonomia gradual. Modulo puro: nao precisa de banco."""

from backend.dominio.autonomia import (
    ACOES,
    DECISAO_POR_ACAO,
    JANELA,
    NIVEIS,
    acoes_a_rebaixar,
    montar,
    pode_promover,
    proximo_nivel,
)
from backend.models.enums import TipoAcao


def decisao(aceita=True, tipo="estimativa", **campos):
    base = {"tipo": tipo, "aceita": aceita, "sugerido": {}, "escolhido": {}}
    base.update(campos)
    return base


def test_acoes_destrutivas_ficam_fora_do_enum():
    """Apagar nunca vira automatico: a garantia e nao existir no enum.

    A lista e explicita, e nao uma contagem: `len(ACOES) == 4` quebrava a
    cada acao nova legitima, e o que importa nao e QUANTAS acoes existem --
    e que nenhuma delas apague nada.
    """
    destrutivas = {
        "apagar_task",
        "apagar_task_propria",
        "apagar_nota",
        "apagar_nota_propria",
        "apagar_evidencia",
    }
    assert destrutivas.isdisjoint(ACOES)
    # Nem por outro nome: qualquer coisa que apaga fica de fora.
    assert not [a for a in ACOES if a.startswith("apagar")]


def test_todo_valor_do_enum_do_banco_esta_no_dominio():
    """O enum do Postgres e a tupla do dominio nao podem divergir.

    Se divergirem, `montar` deixa uma acao sem linha (ou a migration cria
    linha para uma acao que o dominio nao conhece) e a tela mostra um
    painel incompleto, sem erro em lugar nenhum.
    """
    assert {a.value for a in TipoAcao} == set(ACOES)


def test_concluir_com_evidencia_nunca_promove_sozinho():
    """Nao tem tipo de decisao: nao acumula historico, nao sobe na janela.

    E de proposito. O que autorizaria confiar nela nao e uma sequencia de
    escolhas aceitas -- e um humano ter CONFERIDO a prova. Essa promocao e
    na mao, pela tela.
    """
    assert DECISAO_POR_ACAO["concluir_com_evidencia"] is None


# --------------------------------------------------------------------------
# promocao
# --------------------------------------------------------------------------


def test_janela_incompleta_nao_promove():
    saida = pode_promover([decisao() for _ in range(JANELA - 1)])

    assert saida["pode"] is False
    assert f"{JANELA - 1} de {JANELA}" in saida["motivo"]


def test_janela_cheia_e_toda_aceita_promove():
    saida = pode_promover([decisao() for _ in range(JANELA)])

    assert saida["pode"] is True
    assert saida["aceitas_seguidas"] == JANELA
    assert saida["proximo_nivel"] == "confirmar_em_lote"
    assert f"ultimas {JANELA} decisoes foram aceitas" in saida["motivo"]


def test_uma_recusa_na_janela_bloqueia():
    # A recusa e a mais recente: zera a contagem.
    decisoes = [decisao(aceita=False)] + [decisao() for _ in range(JANELA)]

    saida = pode_promover(decisoes)

    assert saida["pode"] is False
    assert saida["aceitas_seguidas"] == 0


def test_recusa_no_fim_da_janela_tambem_bloqueia():
    decisoes = [decisao() for _ in range(JANELA - 1)] + [decisao(aceita=False)]

    saida = pode_promover(decisoes)

    assert saida["pode"] is False
    assert saida["aceitas_seguidas"] == JANELA - 1


def test_recusa_antiga_fora_da_janela_nao_atrapalha():
    decisoes = [decisao() for _ in range(JANELA)] + [decisao(aceita=False)]

    assert pode_promover(decisoes)["pode"] is True


def test_promocao_de_cada_nivel():
    decisoes = [decisao() for _ in range(JANELA)]

    assert pode_promover(decisoes, "perguntar")["proximo_nivel"] == "confirmar_em_lote"
    assert pode_promover(decisoes, "confirmar_em_lote")["proximo_nivel"] == "automatico"

    topo = pode_promover(decisoes, "automatico")
    assert topo["pode"] is False
    assert topo["proximo_nivel"] is None
    assert "mais autonomo" in topo["motivo"]


def test_proximo_nivel_respeita_a_escada():
    assert proximo_nivel("perguntar") == "confirmar_em_lote"
    assert proximo_nivel("automatico") is None
    assert proximo_nivel("inventado") is None


# --------------------------------------------------------------------------
# rebaixamento
# --------------------------------------------------------------------------


def test_recusa_no_automatico_rebaixa_para_confirmar_em_lote():
    niveis = {"definir_estimativa": "automatico"}

    assert acoes_a_rebaixar(decisao(aceita=False), niveis) == {
        "definir_estimativa": "confirmar_em_lote"
    }


def test_ajuste_humano_rebaixa_a_acao_do_campo_corrigido():
    niveis = {"definir_estimativa": "automatico", "definir_prioridade": "automatico"}
    ajuste = decisao(
        aceita=False, tipo="ajuste_humano", sugerido={"estimativa": "M"},
        escolhido={"estimativa": "P"},
    )

    # So a estimativa foi corrigida: a prioridade mantem a autonomia.
    assert acoes_a_rebaixar(ajuste, niveis) == {
        "definir_estimativa": "confirmar_em_lote"
    }


def test_ajuste_em_dois_campos_rebaixa_os_dois():
    niveis = {"definir_estimativa": "automatico", "definir_prioridade": "automatico"}
    ajuste = decisao(
        aceita=False, tipo="ajuste_humano",
        sugerido={"estimativa": "M", "prioridade": "baixa"},
        escolhido={"estimativa": "P", "prioridade": "alta"},
    )

    assert acoes_a_rebaixar(ajuste, niveis) == {
        "definir_estimativa": "confirmar_em_lote",
        "definir_prioridade": "confirmar_em_lote",
    }


def test_decisao_aceita_nao_rebaixa():
    niveis = {"definir_estimativa": "automatico"}

    assert acoes_a_rebaixar(decisao(aceita=True), niveis) == {}


def test_recusa_fora_do_automatico_nao_rebaixa():
    # Em perguntar e confirmar_em_lote o humano ja estava no circuito.
    for nivel in ("perguntar", "confirmar_em_lote"):
        assert acoes_a_rebaixar(decisao(aceita=False), {"definir_estimativa": nivel}) == {}


# --------------------------------------------------------------------------
# retrato completo
# --------------------------------------------------------------------------


def test_montar_traz_as_quatro_acoes_com_o_nivel_atual():
    niveis = {"definir_estimativa": "confirmar_em_lote"}
    decisoes = {"estimativa": [decisao() for _ in range(JANELA)]}

    saida = montar(niveis, decisoes)

    assert set(saida["acoes"]) == set(ACOES)
    assert saida["acoes"]["definir_estimativa"]["nivel"] == "confirmar_em_lote"
    assert saida["acoes"]["definir_estimativa"]["pode"] is True
    assert saida["acoes"]["definir_estimativa"]["proximo_nivel"] == "automatico"
    # Sem historico, o padrao e perguntar e nao promove.
    assert saida["acoes"]["definir_prioridade"]["nivel"] == NIVEIS[0]
    assert saida["acoes"]["definir_prioridade"]["pode"] is False


def test_marcar_bloqueio_nunca_promove_por_falta_de_historico():
    # Nao ha tipo de decisao que alimente essa acao hoje.
    saida = montar({}, {"estimativa": [decisao() for _ in range(JANELA)]})

    assert saida["acoes"]["marcar_bloqueio"]["pode"] is False


def test_e_promocao_so_quando_sobe_a_escada():
    from backend.dominio.autonomia import e_promocao

    assert e_promocao("perguntar", "confirmar_em_lote")
    assert e_promocao("confirmar_em_lote", "automatico")
    assert not e_promocao("automatico", "perguntar")
    assert not e_promocao("perguntar", "perguntar")
    # Nivel desconhecido conta como promocao: na duvida, exige o humano.
    assert e_promocao("perguntar", "deus")
