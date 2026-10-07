"""Testes do access (JWT) e do refresh (opaco).

Modulo puro: nao precisa de banco.
"""

from datetime import datetime, timedelta, timezone

from backend.seguranca.sessao import (
    criar_access,
    expira_em,
    gerar_refresh,
    hash_refresh,
    ler_access,
    refresh_confere,
)

# 32+ bytes: abaixo disso o pyjwt avisa que a chave e fraca para HMAC-SHA256,
# e o backend recusa subir com segredo curto.
SEGREDO = "segredo-de-teste-com-32-bytes-ou-mais"
OUTRO_SEGREDO = "outro-segredo-de-teste-com-32-bytes-ou-mais"

# Instante fixo, usado so onde o teste fala de tempo. O resto parte de agora:
# um instante chumbado no passado faz o token nascer vencido.
AGORA = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


def access(segredo=SEGREDO, minutos=15, agora=None, papel="dev"):
    return criar_access(
        7, 42, papel, segredo, minutos, agora or datetime.now(timezone.utc)
    )


# --------------------------------------------------------------------------
# access
# --------------------------------------------------------------------------


def test_token_valido_devolve_quem_e():
    corpo = ler_access(access(), SEGREDO)

    assert corpo == {"usuario_id": 7, "sessao_id": 42, "papel": "dev"}


def test_token_de_outro_segredo_nao_passa():
    # E o ataque obvio: assinar o proprio token.
    assert ler_access(access(segredo=OUTRO_SEGREDO), SEGREDO) is None


def test_token_mexido_nao_passa():
    token = access()
    # Troca um caractere do meio: a assinatura deixa de fechar.
    quebrado = token[:30] + ("a" if token[30] != "a" else "b") + token[31:]

    assert ler_access(quebrado, SEGREDO) is None


def test_token_expirado_nao_passa():
    velho = criar_access(
        7, 42, "dev", SEGREDO, minutos=15, agora=AGORA - timedelta(hours=2)
    )

    assert ler_access(velho, SEGREDO) is None


def test_token_dentro_da_validade_passa():
    assert ler_access(access(minutos=15), SEGREDO) is not None


def test_lixo_nao_passa():
    for ruim in ("", "abc", "a.b.c", None):
        assert ler_access(ruim or "", SEGREDO) is None


def test_token_sem_os_campos_esperados_nao_passa():
    import jwt

    # Assinado com o nosso segredo, mas sem sub/sid: ainda e recusado.
    torto = jwt.encode({"foo": "bar"}, SEGREDO, algorithm="HS256")

    assert ler_access(torto, SEGREDO) is None


def test_o_papel_viaja_mas_e_informativo():
    """O papel esta no token para a tela desenhar; a API le do banco.

    Este teste documenta a intencao: o valor passa, e por isso ninguem deve
    autorizar por ele.
    """
    corpo = ler_access(access(papel="admin"), SEGREDO)

    assert corpo["papel"] == "admin"


# --------------------------------------------------------------------------
# refresh
# --------------------------------------------------------------------------


def test_refresh_nunca_repete():
    assert gerar_refresh()[0] != gerar_refresh()[0]


def test_o_banco_nao_guarda_o_refresh_em_claro():
    bruto, guardado = gerar_refresh()

    assert bruto != guardado
    assert bruto not in guardado


def test_refresh_certo_confere():
    bruto, guardado = gerar_refresh()

    assert refresh_confere(bruto, guardado)


def test_refresh_errado_nao_confere():
    bruto, guardado = gerar_refresh()
    outro, _ = gerar_refresh()

    assert not refresh_confere(outro, guardado)
    assert not refresh_confere(bruto[:-1], guardado)
    assert not refresh_confere("", guardado)


def test_hash_do_refresh_e_estavel():
    bruto, guardado = gerar_refresh()

    assert hash_refresh(bruto) == guardado


def test_expira_em_soma_os_dias():
    assert expira_em(14, AGORA) == AGORA + timedelta(days=14)
