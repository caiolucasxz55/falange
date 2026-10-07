"""Testes do hash de senha. Modulo puro: nao precisa de banco."""

from backend.seguranca.senha import (
    MAX_SENHA,
    MIN_SENHA,
    gerar_hash,
    senha_aceitavel,
    verificar,
)

SENHA = "senha-de-teste-longa"


def test_senha_certa_confere():
    confere, _ = verificar(SENHA, gerar_hash(SENHA))

    assert confere


def test_senha_errada_nao_confere():
    hash_guardado = gerar_hash(SENHA)

    assert verificar("outra-senha-longa", hash_guardado)[0] is False
    # Guarda contra comparacao por prefixo.
    assert verificar(SENHA[:-1], hash_guardado)[0] is False
    assert verificar(SENHA + "x", hash_guardado)[0] is False


def test_hash_nunca_repete():
    # Salt por hash: duas contas com a mesma senha nao se parecem no banco.
    assert gerar_hash(SENHA) != gerar_hash(SENHA)


def test_o_hash_nao_contem_a_senha():
    assert SENHA not in gerar_hash(SENHA)


def test_hash_ausente_recusa_sem_estourar():
    # E o caso da conta de servico: sem senha, nunca entra por login.
    assert verificar(SENHA, None) == (False, False)
    assert verificar(SENHA, "") == (False, False)


def test_hash_corrompido_recusa_sem_estourar():
    assert verificar(SENHA, "isto-nao-e-um-hash") == (False, False)


def test_hash_atual_nao_pede_regravacao():
    _, regravar = verificar(SENHA, gerar_hash(SENHA))

    assert regravar is False


def test_senha_curta_e_recusada():
    assert senha_aceitavel("a" * (MIN_SENHA - 1)) is not None
    assert str(MIN_SENHA) in senha_aceitavel("curta")


def test_senha_longa_e_recusada():
    assert senha_aceitavel("a" * (MAX_SENHA + 1)) is not None


def test_senha_no_tamanho_passa():
    assert senha_aceitavel("a" * MIN_SENHA) is None
    assert senha_aceitavel("a" * MAX_SENHA) is None
