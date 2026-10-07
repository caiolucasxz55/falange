"""Testes do perfil do time. Modulo puro: nao precisa de banco."""

from backend.dominio.perfil import (
    CONSISTENCIA_MINIMA,
    MINIMO_OCORRENCIAS,
    deve_registrar_ajuste,
    montar,
)


def decisao(tipo="proxima_task", rotulo="destravar", aceita=True, **campos):
    base = {
        "tipo": tipo,
        "sugerido": {},
        "escolhido": {"rotulo": rotulo},
        "aceita": aceita,
        "motivo": None,
        "responsavel": None,
        "task_id": None,
    }
    base.update(campos)
    return base


def ajuste(campo, antes, depois):
    return decisao(
        tipo="ajuste_humano",
        sugerido={campo: antes},
        escolhido={campo: depois},
        aceita=False,
    )


def candidatos(saida):
    return {c["descricao"]: c for c in saida["padroes_candidatos"]}


# --------------------------------------------------------------------------
# deteccao de padrao: no limiar e logo abaixo dele
# --------------------------------------------------------------------------


def test_padrao_no_limiar_de_ocorrencias_e_detectado():
    decisoes = [decisao() for _ in range(MINIMO_OCORRENCIAS)]

    saida = montar(decisoes, [])

    achado = candidatos(saida)["o time escolhe destravar antes de pegar task nova"]
    assert achado["ocorrencias"] == MINIMO_OCORRENCIAS
    assert achado["consistencia"] == 1.0


def test_uma_ocorrencia_abaixo_do_limiar_nao_e_padrao():
    decisoes = [decisao() for _ in range(MINIMO_OCORRENCIAS - 1)]

    assert montar(decisoes, [])["padroes_candidatos"] == []


def test_consistencia_no_limiar_e_detectada():
    # 8 de 10 = 0.8, exatamente o minimo.
    decisoes = [decisao(rotulo="destravar") for _ in range(8)]
    decisoes += [decisao(rotulo="prioritaria") for _ in range(2)]

    achado = candidatos(montar(decisoes, []))
    assert achado["o time escolhe destravar antes de pegar task nova"]["consistencia"] == (
        CONSISTENCIA_MINIMA
    )


def test_consistencia_logo_abaixo_do_limiar_nao_e_padrao():
    # 7 de 10 = 0.7.
    decisoes = [decisao(rotulo="destravar") for _ in range(7)]
    decisoes += [decisao(rotulo="prioritaria") for _ in range(3)]

    assert montar(decisoes, [])["padroes_candidatos"] == []


def test_padrao_que_ja_virou_preferencia_nao_e_oferecido_de_novo():
    decisoes = [decisao() for _ in range(MINIMO_OCORRENCIAS)]
    preferencias = [
        {
            "id": 1,
            "descricao": "o time escolhe destravar antes de pegar task nova",
            "origem": "inferida",
            "ativa": False,
        }
    ]

    # Mesmo inativa, nao se pergunta duas vezes a mesma coisa.
    assert montar(decisoes, preferencias)["padroes_candidatos"] == []


def test_decisao_sem_rotulo_nao_entra_na_deteccao():
    decisoes = [decisao(escolhido={}) for _ in range(MINIMO_OCORRENCIAS)]

    assert montar(decisoes, [])["padroes_candidatos"] == []


def test_padrao_sem_frase_pronta_usa_texto_generico():
    decisoes = [decisao(tipo="pre_task", rotulo="aprovar_todas") for _ in range(MINIMO_OCORRENCIAS)]

    assert "em pre_task, o time escolhe 'aprovar_todas'" in candidatos(montar(decisoes, []))


# --------------------------------------------------------------------------
# frases de ajuste humano
# --------------------------------------------------------------------------


def test_frase_de_ajuste_conta_a_direcao_dominante():
    decisoes = [ajuste("estimativa", "M", "P") for _ in range(7)]
    decisoes += [ajuste("estimativa", "P", "M") for _ in range(3)]

    frases = montar(decisoes, [])["ajustes_comuns"]

    assert "a estimativa da IA foi reduzida em 7 de 10 ajustes" in frases


def test_frase_de_ajuste_para_campo_sem_escala():
    decisoes = [ajuste("bloco", "infra", "backend") for _ in range(3)]

    assert "a bloco da IA foi trocada em 3 de 3 ajustes" in montar(decisoes, [])["ajustes_comuns"]


# --------------------------------------------------------------------------
# aceitacao e preferencias
# --------------------------------------------------------------------------


def test_taxa_de_aceitacao_por_tipo():
    decisoes = [decisao(aceita=True) for _ in range(3)]
    decisoes += [decisao(aceita=False)]

    assert montar(decisoes, [])["aceitacao_por_tipo"]["proxima_task"] == {
        "n": 4,
        "aceitas": 3,
        "taxa": 0.75,
    }


def test_so_preferencia_ativa_entra_no_perfil():
    preferencias = [
        {"id": 1, "descricao": "sempre quebrar G", "origem": "explicita", "ativa": True},
        {"id": 2, "descricao": "nunca mexer em infra", "origem": "inferida", "ativa": False},
    ]

    ativas = montar([], preferencias)["preferencias_ativas"]

    assert [p["id"] for p in ativas] == [1]


# --------------------------------------------------------------------------
# registro automatico de correcao humana
# --------------------------------------------------------------------------


def test_chamada_do_mcp_nao_registra_ajuste():
    # O header diz que quem mexeu foi a propria IA.
    assert not deve_registrar_ajuste("ia", "mcp", {"estimativa": "P"})


def test_chamada_sem_header_registra_ajuste():
    assert deve_registrar_ajuste("ia", None, {"estimativa": "P"})


def test_task_escrita_por_humano_nao_gera_ajuste():
    # Humano corrigindo humano nao ensina nada sobre a IA.
    assert not deve_registrar_ajuste("humano", None, {"estimativa": "P"})


def test_campo_de_texto_nao_conta_como_correcao_de_julgamento():
    assert not deve_registrar_ajuste("ia", None, {"titulo": "outro titulo"})
    assert deve_registrar_ajuste("ia", None, {"titulo": "outro", "prioridade": "alta"})
