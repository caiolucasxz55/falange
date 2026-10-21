"""Extracao dos criterios das descricoes antigas (migration 0010) e o lint
que julga os criterios novos (template do MCP).

A extracao e testada com descricoes copiadas do banco real: o valor dela
nao e casar com um regex bonito, e sim nao perder nem corromper o que o time
ja escreveu.
"""

import importlib.util
import pathlib

import pytest

from falange_mcp.template import validar_criterios, validar_pre_task

# A migration nao e importavel por nome (`0010_criterio` nao e identificador),
# entao carrega pelo caminho. Testar a funcao DENTRO dela e de proposito:
# copiar a logica para ca deixaria a copia passando e a migration errada.
_CAMINHO = (
    pathlib.Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0010_criterio.py"
)
_spec = importlib.util.spec_from_file_location("migracao_0010", _CAMINHO)
migracao = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migracao)


# --------------------------------------------------------------- extracao


def test_extrai_criterio_inline_no_fim_do_paragrafo():
    # Task #70 do banco real: o marcador vem no meio do paragrafo.
    descricao = (
        "Trocar o historico de requisicoes em memoria por Redis, para o teto "
        "valer entre replicas. Criterio de aceite: com duas replicas atras do "
        "proxy, o teto por cliente e respeitado no conjunto."
    )
    assert migracao.extrair(descricao) == [
        "com duas replicas atras do proxy, o teto por cliente e respeitado "
        "no conjunto."
    ]


def test_extrai_criterio_apos_quebra_de_linha():
    # Task #1 do banco real: o marcador abre a propria linha.
    descricao = (
        "Percorrer a cadeia de bloqueio e recusar com 409.\n"
        "Criterio de aceite: A trava B, travar A por B retorna 409."
    )
    assert migracao.extrair(descricao) == [
        "A trava B, travar A por B retorna 409."
    ]


def test_extrai_com_acento_no_marcador_sem_estragar_o_texto():
    descricao = (
        "Fazer a validacao da sessão.\n"
        "Critério de aceite: o cookie não volta no corpo da resposta."
    )
    # O acento do criterio sobrevive: a busca e sem acento, o corte e no
    # texto original.
    assert migracao.extrair(descricao) == [
        "o cookie não volta no corpo da resposta."
    ]


def test_um_criterio_por_bullet_quando_ha_bullet():
    descricao = (
        "Fazer a coisa.\n"
        "Criterio de aceite:\n"
        "- retorna 409 no ciclo\n"
        "- a task aparece no board\n"
    )
    assert migracao.extrair(descricao) == [
        "retorna 409 no ciclo",
        "a task aparece no board",
    ]


def test_descricao_sem_criterio_ou_vazia_nao_inventa_nada():
    # Task #4 do banco real tem descricao vazia.
    assert migracao.extrair("") == []
    assert migracao.extrair(None) == []
    assert migracao.extrair("Criada por fora da tela, sem mais.") == []


def test_texto_longo_e_cortado_visivelmente_em_vez_de_recusado():
    longo = "x" * 300
    (extraido,) = migracao.extrair(f"Faz a coisa.\nCriterio de aceite: {longo}")
    assert len(extraido) == 200
    assert extraido.endswith("...")


def test_nunca_passa_do_teto_de_cinco():
    bullets = "\n".join(f"- criterio observavel numero {i}" for i in range(9))
    assert len(migracao.extrair(f"Faz.\nCriterio de aceite:\n{bullets}")) == 5


# ------------------------------------------------------------------- lint


def test_criterio_observavel_passa():
    assert validar_criterios(["o endpoint retorna 409 no ciclo"]) == []


def test_recusa_lista_vazia_e_lista_grande():
    assert "ao menos 1" in " ".join(validar_criterios([]))
    assert "no maximo 5" in " ".join(
        validar_criterios(["o endpoint retorna 409 aqui"] * 6)
    )


@pytest.mark.parametrize(
    "texto",
    [
        "funcionar bem",
        "o login deve funcionar corretamente",
        "melhorar a performance da tela",
        "ficar mais rapido",
        "o codigo fica mais limpo e organizado",
    ],
)
def test_recusa_intencao_disfarcada_de_criterio(texto):
    motivos = " ".join(validar_criterios([texto]))
    assert motivos, f"{texto!r} passou, e e intencao"


def test_recusa_criterio_sem_nada_de_observavel():
    motivos = " ".join(validar_criterios(["a parte de backend da feature"]))
    assert "observavel" in motivos


def test_recusa_enchimento_dentro_do_criterio():
    motivos = " ".join(validar_criterios(["retorna 409, 422 e afins"]))
    assert "enchimento" in motivos


def test_recusa_criterio_curto_ou_longo():
    assert "curto" in " ".join(validar_criterios(["retorna"]))
    assert "chars" in " ".join(validar_criterios(["retorna 409 " + "x" * 300]))


def test_recusa_criterios_repetidos():
    repetido = "o endpoint retorna 409 no ciclo"
    motivos = " ".join(validar_criterios([repetido, repetido.upper()]))
    assert "repetido" in motivos


# ------------------------------------------- integracao com a pre-task


def _pre_task(**campos):
    base = {
        "titulo": "Validar expiracao do token no login",
        "descricao": (
            "Fazer o login recusar access token vencido e devolver 401, para a "
            "sessao nao sobreviver ao vencimento."
        ),
        "estimativa": "P",
        "bloco": "backend",
    }
    return {**base, **campos}


def test_pre_task_com_lista_de_criterios_dispensa_a_linha_na_descricao():
    saida = validar_pre_task(
        _pre_task(criterios=["o login com token vencido retorna 401"])
    )
    assert saida["veredito"] == "aprovada", saida["motivos"]


def test_pre_task_sem_criterio_nenhum_reprova():
    saida = validar_pre_task(_pre_task())
    assert saida["veredito"] == "precisa_de_ajuste"
    assert any("criterio de aceite" in m for m in saida["motivos"])


def test_pre_task_antiga_com_a_linha_na_descricao_continua_valendo():
    """Compatibilidade: `/falange-gerar` ja escrevia a linha, nao a lista."""
    saida = validar_pre_task(
        _pre_task(
            descricao=(
                "Fazer o login recusar access token vencido, para a sessao nao "
                "sobreviver ao vencimento.\n"
                "Criterio de aceite: o login com token vencido retorna 401."
            )
        )
    )
    assert saida["veredito"] == "aprovada", saida["motivos"]
    # A linha vira lista estruturada na saida, para quem chama nao ter de
    # reparsear a descricao.
    assert saida["criterios"] == ["o login com token vencido retorna 401."]


def test_criterio_ruim_reprova_a_pre_task_inteira():
    saida = validar_pre_task(_pre_task(criterios=["funcionar bem"]))
    assert saida["veredito"] == "precisa_de_ajuste"
