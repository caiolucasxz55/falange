"""Testes da normalizacao dos nomes de pessoa. Nao precisam de banco.

O defeito que estes testes guardam nao era cosmetico. Com o texto gravado
sujo:

- o filtro `?responsavel=Caio` nao achava a task gravada como `"Caio "`;
- `/carga` contava zero e a sobrecarga ficava silenciosamente errada;
- `responsavel_id` nunca resolvia, porque a busca por nome compara o texto
  aparado da entrada com o nome do usuario, gravado com espaco;
- e "sem responsavel" tinha tres grafias na mesma coluna: None, "" e "   ".
"""

import pytest
from pydantic import ValidationError

from backend.schemas.aprendizado import DecisaoNova
from backend.schemas.nota import NotaEdicao, NotaNova
from backend.schemas.task import TaskEdicao, TaskNova
from backend.schemas.texto import MAX_NOME
from backend.schemas.usuario import UsuarioEdicao, UsuarioNovo


def task(**campos):
    return TaskNova(titulo="Titulo qualquer", estimativa="PP", bloco="infra", **campos)


# --------------------------------------------------------------------------
# aparar
# --------------------------------------------------------------------------


def test_apara_os_dois_lados():
    assert task(responsavel="  Caio  ").responsavel == "Caio"


def test_apara_tambem_no_autor_da_nota_e_na_decisao():
    assert NotaNova(texto="texto suficiente", autor=" Caio ").autor == "Caio"
    assert DecisaoNova(tipo="estimativa", aceita=True, responsavel=" Caio ").responsavel == "Caio"


def test_apara_o_nome_do_usuario():
    """Sem isto, a FK do responsavel nunca casa.

    `buscar_por_nome` apara a entrada e compara com o `nome` gravado; nome
    gravado com espaco nao casa com nada.
    """
    novo = UsuarioNovo(email="a@b.com", nome="  Caio  ", senha="senha-boa-aqui")

    assert novo.nome == "Caio"
    assert UsuarioEdicao(nome="  Caio  ").model_dump(exclude_unset=True) == {"nome": "Caio"}


def test_nome_no_meio_nao_e_tocado():
    # Aparar e nas pontas: "Ana Maria" nao vira "AnaMaria".
    assert task(responsavel="  Ana Maria  ").responsavel == "Ana Maria"


# --------------------------------------------------------------------------
# uma representacao so para "sem responsavel"
# --------------------------------------------------------------------------


@pytest.mark.parametrize("entrada", ["", "   ", "\t", "\n"])
def test_vazio_em_qualquer_grafia_vira_ausencia(entrada):
    assert task(responsavel=entrada).responsavel is None


def test_omitir_tambem_e_ausencia():
    assert task().responsavel is None


@pytest.mark.parametrize("entrada", ["", "  ", None])
def test_na_edicao_vazio_remove_o_responsavel(entrada):
    """A convencao do MCP (`responsavel=""` remove) agora vale para todo
    cliente, e grava sempre o mesmo valor."""
    assert TaskEdicao(responsavel=entrada).model_dump(exclude_unset=True) == {
        "responsavel": None
    }


def test_na_edicao_vazio_tambem_solta_o_autor_da_nota():
    assert NotaEdicao(autor="  ").model_dump(exclude_unset=True) == {"autor": None}


# --------------------------------------------------------------------------
# o teto de tamanho continua valendo, e mede o valor aparado
# --------------------------------------------------------------------------


def test_nome_longo_demais_e_recusado():
    with pytest.raises(ValidationError):
        task(responsavel="a" * (MAX_NOME + 1))


def test_nome_no_limite_com_espaco_em_volta_passa():
    # Mede o aparado: senao o espaco gastaria do teto.
    assert task(responsavel="  " + "a" * MAX_NOME + "  ").responsavel == "a" * MAX_NOME


def test_nome_de_usuario_so_com_espaco_e_recusado():
    # Obrigatorio: nao vira None, cai no min_length.
    with pytest.raises(ValidationError):
        UsuarioNovo(email="a@b.com", nome="   ", senha="senha-boa-aqui")


def test_nome_de_usuario_curto_demais_e_recusado():
    with pytest.raises(ValidationError):
        UsuarioNovo(email="a@b.com", nome=" a ", senha="senha-boa-aqui")
