"""Testes da matriz de papeis. Modulo puro: nao precisa de banco."""

import pytest

from backend.dominio.papeis import (
    ACOES,
    PAPEIS,
    PAPEIS_HUMANOS,
    PAPEL_IA,
    PERMISSOES,
    PRIORIDADE_PADRAO,
    acoes_de,
    acoes_para_campos,
    papel_valido,
    pode,
)


def test_todo_papel_tem_linha_na_matriz():
    # Papel sem linha nao alcancaria nada e o 403 pareceria um bug.
    assert set(PERMISSOES) == set(PAPEIS)


def test_a_matriz_nao_cita_acao_inexistente():
    # Um nome errado na matriz seria permissao que nunca e consultada.
    for papel, acoes in PERMISSOES.items():
        assert acoes <= set(ACOES), f"{papel} cita acao fora de ACOES"


def test_todo_mundo_le():
    for papel in PAPEIS:
        assert pode(papel, "ler")


def test_leitor_so_le():
    assert acoes_de("leitor") == ["ler"]


def test_admin_alcanca_tudo():
    assert set(acoes_de("admin")) == set(ACOES)


# --------------------------------------------------------------------------
# a escada dos papeis humanos
# --------------------------------------------------------------------------


def test_a_escada_humana_nunca_inverte():
    """Cada papel humano alcanca um subconjunto do papel acima dele.

    Se um dev pudesse algo que um lead nao pode, a escada deixaria de ser
    escada e a tela nao teria como explicar o 403 para ninguem.
    """
    for acima, abaixo in zip(PAPEIS_HUMANOS, PAPEIS_HUMANOS[1:]):
        assert PERMISSOES[abaixo] < PERMISSOES[acima], f"{abaixo} nao cabe em {acima}"


@pytest.mark.parametrize("acao", ["definir_configuracao", "gerir_usuarios"])
def test_so_admin_mexe_na_plataforma(acao):
    assert pode("admin", acao)
    for papel in ("lead", "dev", "leitor", PAPEL_IA):
        assert not pode(papel, acao)


@pytest.mark.parametrize("acao", ["definir_prioridade", "atribuir_responsavel"])
def test_decidir_o_trabalho_e_de_admin_e_lead(acao):
    assert pode("admin", acao)
    assert pode("lead", acao)
    assert not pode("dev", acao)
    assert not pode("leitor", acao)


def test_dev_executa_mas_nao_prioriza():
    assert pode("dev", "criar_task")
    assert pode("dev", "mudar_status_task")
    assert pode("dev", "marcar_bloqueio")
    assert not pode("dev", "definir_prioridade")


def test_dev_apaga_so_o_que_e_dele():
    assert not pode("dev", "apagar_task")
    assert pode("dev", "apagar_task_propria")
    assert not pode("dev", "apagar_nota")
    assert pode("dev", "apagar_nota_propria")


def test_lead_apaga_do_time():
    assert pode("lead", "apagar_task")
    assert pode("lead", "apagar_nota")


# --------------------------------------------------------------------------
# a IA: trabalha, mas nao eleva a confianca em si mesma
# --------------------------------------------------------------------------


def test_ia_trabalha_como_dev():
    assert pode(PAPEL_IA, "criar_task")
    assert pode(PAPEL_IA, "editar_task")
    assert pode(PAPEL_IA, "marcar_bloqueio")
    assert pode(PAPEL_IA, "registrar_decisao")
    assert pode(PAPEL_IA, "criar_preferencia")


@pytest.mark.parametrize("acao", ["ativar_preferencia", "promover_autonomia"])
def test_ia_nao_eleva_a_confianca_em_si_mesma(acao):
    """A trava central do projeto: a IA propoe, o humano confirma."""
    assert not pode(PAPEL_IA, acao)
    assert pode("admin", acao)
    assert pode("lead", acao)


def test_rebaixar_autonomia_e_livre_para_quem_trabalha():
    # Descer confianca e seguro: nao exige humano.
    for papel in ("admin", "lead", "dev", PAPEL_IA):
        assert pode(papel, "rebaixar_autonomia")
    assert not pode("leitor", "rebaixar_autonomia")


def test_ia_nao_e_um_papel_humano():
    assert PAPEL_IA not in PAPEIS_HUMANOS


def test_ia_nao_mexe_em_usuario_nem_na_plataforma():
    assert not pode(PAPEL_IA, "gerir_usuarios")
    assert not pode(PAPEL_IA, "definir_configuracao")


# --------------------------------------------------------------------------
# na duvida, barra
# --------------------------------------------------------------------------


def test_papel_desconhecido_nao_alcanca_nada():
    for papel in ("root", "", None, "ADMIN"):
        assert not pode(papel, "ler")
        assert not pode(papel, "criar_task")
        assert acoes_de(papel) == []


def test_acao_desconhecida_e_sempre_negada():
    # Erro de digitacao no nome da acao nao pode abrir a porta.
    assert not pode("admin", "apagar_o_banco")
    assert not pode("admin", "")


def test_papel_valido_so_aceita_os_cinco():
    for papel in PAPEIS:
        assert papel_valido(papel)
    for papel in ("root", "", None, "Admin"):
        assert not papel_valido(papel)


# --------------------------------------------------------------------------
# que campos exigem permissao extra
# --------------------------------------------------------------------------


def test_campo_inocente_nao_exige_nada():
    assert acoes_para_campos({"titulo": "x", "descricao": "y"}, "caio") == set()
    assert acoes_para_campos({}, "caio") == set()


def test_prioridade_padrao_nao_exige_nada():
    # Senao um dev nao conseguiria abrir task nenhuma.
    assert acoes_para_campos({"prioridade": PRIORIDADE_PADRAO}, "caio") == set()


def test_prioridade_diferente_do_padrao_exige_permissao():
    for valor in ("alta", "baixa"):
        assert acoes_para_campos({"prioridade": valor}, "caio") == {
            "definir_prioridade"
        }


def test_prioridade_aceita_enum():
    # As rotas passam o Enum do SQLAlchemy, nao a string.
    class Falso:
        value = "alta"

    assert acoes_para_campos({"prioridade": Falso()}, "caio") == {
        "definir_prioridade"
    }


def test_atribuir_a_si_mesmo_nao_exige_permissao():
    assert acoes_para_campos({"responsavel": "caio"}, "caio") == set()
    # Caixa e espaco nao deveriam mudar o veredito.
    assert acoes_para_campos({"responsavel": " Caio "}, "caio") == set()


def test_atribuir_a_outro_exige_permissao():
    assert acoes_para_campos({"responsavel": "outra pessoa"}, "caio") == {
        "atribuir_responsavel"
    }


def test_limpar_o_responsavel_nao_exige_permissao():
    # Abrir mao da task nao e distribuir trabalho.
    assert acoes_para_campos({"responsavel": None}, "caio") == set()
    assert acoes_para_campos({"responsavel": ""}, "caio") == set()


def test_sem_nome_do_chamador_atribuir_sempre_exige():
    # Caso da tela sem login: nao da para provar que e voce mesmo.
    assert acoes_para_campos({"responsavel": "caio"}, None) == {
        "atribuir_responsavel"
    }


def test_os_dois_campos_somam_as_exigencias():
    campos = {"prioridade": "alta", "responsavel": "outra pessoa"}

    assert acoes_para_campos(campos, "caio") == {
        "definir_prioridade",
        "atribuir_responsavel",
    }
