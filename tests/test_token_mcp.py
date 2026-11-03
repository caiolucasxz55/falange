"""Token de conexao do MCP: formato, validacao e as rotas sem chamador.

O modulo de formato e puro, entao a maior parte aqui nao precisa de banco.
O ultimo bloco e diferente: ele audita o FONTE das rotas, e existe porque
o porteiro do middleware passou a aceitar o formato do token sem conferir
o hash -- o que so e seguro enquanto toda rota que faz algo resolver o
chamador.
"""

import pathlib
import re

import pytest

from backend.repositorio.tokens_mcp import token_vivo
from backend.seguranca.token import entrada_permitida
from backend.seguranca.token_mcp import (
    MARCA,
    TAM_PREFIXO,
    confere,
    gerar,
    hash_do_segredo,
    nome_aceitavel,
    partes,
)

# ---------------------------------------------------------------- formato


def test_gerar_devolve_token_prefixo_e_hash_coerentes():
    token, prefixo, hash_segredo = gerar()
    assert token.startswith(f"{MARCA}_")
    assert len(prefixo) == TAM_PREFIXO
    # O prefixo esta DENTRO do token, para o servidor achar a linha.
    assert token.split("_")[1] == prefixo
    # sha256 hex.
    assert re.fullmatch(r"[0-9a-f]{64}", hash_segredo)


def test_o_segredo_nao_esta_no_hash():
    """Obvio, e justamente por isso tem teste: e a garantia do desenho."""
    token, _, hash_segredo = gerar()
    segredo = token.split("_", 2)[2]
    assert segredo not in hash_segredo
    assert hash_do_segredo(segredo) == hash_segredo


def test_todo_token_gerado_se_parseia_de_volta():
    """O gerador e o parser tem de concordar SEMPRE, nao quase sempre.

    Este teste existe por causa de um bug de verdade: o prefixo vinha de
    `secrets.token_urlsafe`, cujo alfabeto inclui `_` -- que e o SEPARADOR
    do token. Um prefixo com `_` partia o token no lugar errado e produzia
    uma credencial que nunca se parseava. 12,9% dos tokens nasciam
    quebrados, em silencio, e so falhavam na hora de conectar.

    500 rodadas, e nao uma: o bug aparecia em 1 de 8, entao um unico
    `gerar()` passaria na maior parte das vezes -- e foi assim que ele
    chegou a ser commitado.
    """
    for _ in range(500):
        token, prefixo, _hash = gerar()
        separado = partes(token)
        assert separado is not None, f"nao se parseia: {token}"
        assert separado[0] == prefixo, f"prefixo errado: {token}"


def test_o_prefixo_nunca_contem_o_separador():
    """A causa raiz, cobrada direto."""
    for _ in range(500):
        _token, prefixo, _hash = gerar()
        assert "_" not in prefixo
        assert prefixo.isalnum()


def test_dois_tokens_nunca_saem_iguais():
    tokens = {gerar()[0] for _ in range(50)}
    prefixos = {gerar()[1] for _ in range(50)}
    assert len(tokens) == 50
    assert len(prefixos) == 50


def test_separa_prefixo_e_segredo():
    token, prefixo, _ = gerar()
    assert partes(token) == (prefixo, token.split("_", 2)[2])


@pytest.mark.parametrize(
    "lixo",
    [
        None,
        "",
        "flg",
        "flg_curto",
        "flg_abc_def",            # prefixo de tamanho errado
        "xxx_12345678_segredo",   # marca errada
        "flg_12345678_",          # sem segredo
        "flg_12345678",           # sem a terceira parte
        # Um JWT: o formato tem de nao casar, senao o porteiro trataria
        # todo access token como token de conexao.
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def",
    ],
)
def test_nao_confunde_com_outra_coisa(lixo):
    assert partes(lixo) is None


def test_segredo_com_underscore_sobrevive():
    """`split` com maxsplit=2: o segredo em base64 urlsafe nao tem `_`,
    mas se um dia tiver, nao pode ser cortado pela metade."""
    assert partes("flg_12345678_a_b_c") == ("12345678", "a_b_c")


def test_confere_so_o_segredo_certo():
    token, _, hash_segredo = gerar()
    segredo = token.split("_", 2)[2]
    assert confere(segredo, hash_segredo) is True
    assert confere(segredo + "x", hash_segredo) is False
    assert confere("", hash_segredo) is False
    # Hash ausente e recusa, nao erro: e o caso de prefixo inexistente.
    assert confere(segredo, None) is False


def test_nome_precisa_dizer_algo():
    assert nome_aceitavel("meu notebook") is None
    assert nome_aceitavel("x") is not None
    assert nome_aceitavel("   ") is not None
    assert nome_aceitavel("x" * 200) is not None


# -------------------------------------------------------------- validade


class TokenFalso:
    def __init__(self, revogado_em=None, expira_em=None):
        self.revogado_em = revogado_em
        self.expira_em = expira_em


def test_token_sem_prazo_vale_ate_revogar():
    """Diferenca proposital em relacao a sessao: `expira_em` nulo vale.

    Exigir prazo faria a conexao da pessoa morrer sozinha no meio de uma
    sessao de trabalho.
    """
    assert token_vivo(TokenFalso()) is True


def test_token_revogado_nao_vale():
    from datetime import datetime, timezone

    agora = datetime(2026, 10, 29, tzinfo=timezone.utc)
    assert token_vivo(TokenFalso(revogado_em=agora)) is False


def test_token_vencido_nao_vale():
    from datetime import datetime, timedelta, timezone

    agora = datetime(2026, 10, 29, tzinfo=timezone.utc)
    assert token_vivo(TokenFalso(expira_em=agora - timedelta(days=1)), agora) is False
    assert token_vivo(TokenFalso(expira_em=agora + timedelta(days=1)), agora) is True


def test_token_inexistente_nao_vale():
    assert token_vivo(None) is False


# --------------------------------------------------------------- porteiro


def test_porteiro_aceita_as_tres_credenciais():
    token, _, _ = gerar()
    compartilhado = "segredo-do-servidor"

    # 1. token compartilhado
    assert entrada_permitida(f"Bearer {compartilhado}", compartilhado, False)
    # 2. JWT (ja conferido pelo middleware)
    assert entrada_permitida("Bearer qualquer.jwt.aqui", compartilhado, True)
    # 3. token de conexao, pelo formato
    assert entrada_permitida(
        f"Bearer {token}", compartilhado, False, parece_token_mcp=True
    )


def test_porteiro_recusa_quem_nao_tem_nenhuma():
    assert not entrada_permitida("Bearer nada", "segredo", False, False)
    assert not entrada_permitida(None, "segredo", False, False)


# ------------------------------------------- as rotas sem obter_chamador


RAIZ = pathlib.Path(__file__).resolve().parent.parent

# Rotas que PODEM existir sem resolver o chamador, e por que:
#
# - `/health`: o docker bate nela antes de qualquer configuracao.
# - login e renovar: autenticam por conta propria, com senha ou refresh.
#
# A lista e fechada de proposito. O porteiro do middleware aceita o
# FORMATO do token de conexao sem conferir o hash, e isso so e seguro
# enquanto toda rota que faz algo resolver o chamador de verdade. Uma rota
# nova sem `obter_chamador` seria alcancavel com um token inventado.
SEM_CHAMADOR_ESPERADO = {
    ("saude.py", "/health"),
    ("sessao.py", "/sessao"),
    ("sessao.py", "/sessao/renovar"),
}

_DECORADOR = re.compile(r'^@rotas\.(get|post|patch|put|delete)\(\s*\n?\s*"([^"]+)"', re.M)


def rotas_declaradas():
    """(arquivo, caminho, corpo da funcao) para cada rota de `backend/rotas/`."""
    achadas = []
    for caminho in sorted((RAIZ / "backend" / "rotas").glob("*.py")):
        texto = caminho.read_text(encoding="utf-8")
        marcas = list(_DECORADOR.finditer(texto))
        for i, marca in enumerate(marcas):
            fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
            achadas.append((caminho.name, marca.group(2), texto[marca.start():fim]))
    return achadas


def test_a_varredura_de_rotas_acha_alguma_coisa():
    """Sem isto, um regex quebrado faria o teste abaixo passar vazio."""
    declaradas = rotas_declaradas()
    assert len(declaradas) > 30, f"achou so {len(declaradas)} rotas"
    assert any(c == "/tasks" for _, c, _ in declaradas)


def test_toda_rota_resolve_o_chamador_menos_as_tres_conhecidas():
    sem = {
        (arquivo, caminho)
        for arquivo, caminho, corpo in rotas_declaradas()
        if "obter_chamador" not in corpo
    }
    assert sem == SEM_CHAMADOR_ESPERADO, (
        "mudou o conjunto de rotas sem obter_chamador. Uma rota nova sem ele "
        "e alcancavel com um token de conexao INVENTADO, porque o middleware "
        "so confere o formato. Se a rota realmente dispensa identidade, "
        "acrescente em SEM_CHAMADOR_ESPERADO dizendo por que."
    )


# ----------------------------------------------- a resposta da criacao


class LinhaFalsa:
    """Uma linha de `token_mcp` como o banco devolve: SEM o segredo."""

    def __init__(self):
        from datetime import datetime, timezone

        self.id = 7
        self.nome = "meu notebook"
        self.prefixo = "abcd1234"
        self.projeto_id = 1
        self.criado_em = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.ultimo_uso_em = None
        self.expira_em = None
        self.revogado_em = None


def test_a_linha_do_banco_nao_valida_como_token_criado():
    """`TokenMCPCriado` exige `token`, e a linha nao tem. E de proposito.

    Este teste documenta um 500 que aconteceu: a rota validava a linha
    direto como `TokenMCPCriado` e atribuia o segredo DEPOIS -- tarde, a
    validacao ja tinha estourado. So a verificacao ponta a ponta pegou:
    nenhum teste de schema olhava a composicao.

    A correcao nao foi dar default a `token`. Default faria um segredo
    VAZIO passar em silencio, e a pessoa receberia 201 com um token que
    nao conecta -- pior que o 500.
    """
    from pydantic import ValidationError

    from backend.schemas.token_mcp import TokenMCPCriado

    with pytest.raises(ValidationError):
        TokenMCPCriado.model_validate(LinhaFalsa(), from_attributes=True)


def test_monta_a_resposta_da_linha_mais_o_segredo():
    """O caminho que a rota usa de verdade."""
    from backend.schemas.token_mcp import TokenMCPCriado, TokenMCPOut

    token, _prefixo, _hash = gerar()
    saida = TokenMCPCriado(
        **TokenMCPOut.model_validate(LinhaFalsa(), from_attributes=True).model_dump(),
        token=token,
    )
    assert saida.token == token
    assert saida.nome == "meu notebook"
    assert saida.prefixo == "abcd1234"
    assert "nao volta a aparecer" in saida.aviso


def test_o_schema_de_listagem_nao_tem_campo_de_segredo():
    """A garantia estrutural: nao ha como vazar por reaproveitar o contrato."""
    from backend.schemas.token_mcp import TokenMCPOut

    assert "token" not in TokenMCPOut.model_fields
