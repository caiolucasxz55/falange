"""Testes do limite de requisicoes. Modulo puro: nao precisa de banco."""

from backend.dominio.limite import permitido, segundos_para_liberar


def test_passa_ate_o_teto():
    historico = []
    for i in range(3):
        passa, historico = permitido(historico, agora=1000.0 + i, maximo=3, janela=60)
        assert passa

    passa, _ = permitido(historico, agora=1003.0, maximo=3, janela=60)
    assert not passa


def test_horario_fora_da_janela_e_descartado():
    # Tres chamadas antigas nao contam: a janela e de 60s.
    antigas = [100.0, 101.0, 102.0]

    passa, historico = permitido(antigas, agora=200.0, maximo=3, janela=60)

    assert passa
    assert historico == [200.0]


def test_janela_desliza_e_libera_aos_poucos():
    historico = [100.0, 150.0, 151.0]

    # Em 165 a primeira (100) ja saiu: sobram duas, cabe mais uma.
    passa, historico = permitido(historico, agora=165.0, maximo=3, janela=60)
    assert passa
    assert 100.0 not in historico


def test_maximo_zero_desliga_o_limite():
    passa, historico = permitido([1.0] * 999, agora=1.0, maximo=0)

    assert passa
    assert historico == []


def test_segundos_para_liberar_usa_a_mais_antiga():
    assert segundos_para_liberar([100.0, 130.0], agora=140.0, janela=60) == 21
    assert segundos_para_liberar([], agora=140.0) is None
