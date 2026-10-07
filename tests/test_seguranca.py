"""Testes da verificacao de token. Modulo puro: nao precisa de banco."""

from backend.seguranca import exige_token, token_valido

SEGREDO = "token-secreto-de-teste"


def test_token_certo_passa():
    assert token_valido(f"Bearer {SEGREDO}", SEGREDO)


def test_token_errado_nao_passa():
    assert not token_valido("Bearer outro-token", SEGREDO)


def test_header_ausente_ou_malformado_nao_passa():
    assert not token_valido(None, SEGREDO)
    assert not token_valido("", SEGREDO)
    # Sem o prefixo Bearer nao vale, mesmo com o segredo correto.
    assert not token_valido(SEGREDO, SEGREDO)
    assert not token_valido(f"Basic {SEGREDO}", SEGREDO)


def test_prefixo_do_token_nao_passa():
    # Guarda contra comparacao por prefixo.
    assert not token_valido(f"Bearer {SEGREDO[:-1]}", SEGREDO)
    assert not token_valido(f"Bearer {SEGREDO}x", SEGREDO)


def test_sem_token_configurado_a_porta_fica_aberta():
    # Dev local: nada configurado, tudo passa. E o padrao, e e intencional.
    assert token_valido(None, "")
    assert token_valido("Bearer qualquer", "")


def test_health_responde_sem_token():
    assert not exige_token("/health", "GET", SEGREDO)


def test_demais_caminhos_exigem_token():
    assert exige_token("/tasks", "GET", SEGREDO)
    assert exige_token("/notas", "POST", SEGREDO)
    assert exige_token("/autonomia/definir_estimativa", "PATCH", SEGREDO)
    assert exige_token("/docs", "GET", SEGREDO)


def test_preflight_nao_exige_token():
    # O preflight nao manda header e nao le dado nenhum.
    assert not exige_token("/tasks", "OPTIONS", SEGREDO)


def test_sem_segredo_configurado_nada_e_exigido():
    assert not exige_token("/tasks", "GET", "")


# --------------------------------------------------------------------------
# a porta aceita DUAS credenciais pelo mesmo header
# --------------------------------------------------------------------------


def test_token_compartilhado_abre_a_porta():
    from backend.seguranca import entrada_permitida

    assert entrada_permitida(f"Bearer {SEGREDO}", SEGREDO, False)


def test_access_token_valido_abre_a_porta_sem_o_compartilhado():
    from backend.seguranca import entrada_permitida

    # Regressao: a primeira versao conferia so o token compartilhado, e todo
    # usuario logado levava 401 antes de a rota existir.
    assert entrada_permitida("Bearer um.jwt.qualquer", SEGREDO, True)


def test_sem_nenhuma_das_duas_a_porta_fica_fechada():
    from backend.seguranca import entrada_permitida

    assert not entrada_permitida("Bearer errado", SEGREDO, False)
    assert not entrada_permitida(None, SEGREDO, False)


def test_sem_segredo_configurado_a_porta_abre_para_qualquer_um():
    from backend.seguranca import entrada_permitida

    assert entrada_permitida(None, "", False)
