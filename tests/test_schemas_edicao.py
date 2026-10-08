"""Testes dos schemas de edicao parcial. Nao precisam de banco.

O assunto e um so: `null` explicito. Num schema de edicao todo campo e
`Optional[...] = None`, porque e assim que "nao enviado" se escreve -- e por
isso `{"campo": null}` chegava indistinguivel de "nao enviei" e ia para uma
coluna NOT NULL, virando 500. Nulo continua valendo onde significa algo.
"""

import pytest
from pydantic import ValidationError

from backend.models.enums import Bloco, Estimativa, Prioridade
from backend.models.usuario import Papel
from backend.schemas.nota import NotaEdicao
from backend.schemas.task import TaskEdicao
from backend.schemas.usuario import UsuarioEdicao


def recusa(modelo, dados) -> str:
    with pytest.raises(ValidationError) as erro:
        modelo.model_validate(dados)
    return str(erro.value)


# --------------------------------------------------------------------------
# usuario: nome, papel e ativo sao NOT NULL
# --------------------------------------------------------------------------


@pytest.mark.parametrize("campo", ["nome", "papel", "ativo"])
def test_usuario_recusa_nulo_explicito(campo):
    assert campo in recusa(UsuarioEdicao, {campo: None})


def test_usuario_papel_nulo_nao_dribla_a_guarda_do_ultimo_admin():
    """Regressao: era assim que se derrubava o unico admin.

    `{"papel": null}` sobrevivia ao `exclude_unset`, a guarda testava
    `is not None` e deixava passar, e o NULL ia para a coluna NOT NULL.
    """
    assert "papel" in recusa(UsuarioEdicao, {"papel": None})


def test_usuario_aceita_edicao_normal():
    body = UsuarioEdicao.model_validate({"papel": "lead"})

    assert body.model_dump(exclude_unset=True) == {"papel": Papel.lead}


def test_usuario_campo_ausente_continua_ausente():
    # A base da edicao parcial: o que nao veio nao e tocado.
    assert UsuarioEdicao.model_validate({}).model_dump(exclude_unset=True) == {}


# --------------------------------------------------------------------------
# task: responsavel aceita nulo; o resto nao
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "campo", ["titulo", "descricao", "estimativa", "bloco", "prioridade"]
)
def test_task_recusa_nulo_nos_campos_obrigatorios(campo):
    assert campo in recusa(TaskEdicao, {campo: None})


def test_task_aceita_nulo_no_responsavel():
    # Nulo aqui significa algo: tirar o responsavel da task.
    body = TaskEdicao.model_validate({"responsavel": None})

    assert body.model_dump(exclude_unset=True) == {"responsavel": None}


def test_task_aceita_edicao_normal():
    body = TaskEdicao.model_validate(
        {"titulo": "Novo titulo", "estimativa": "P", "bloco": "infra"}
    )

    assert body.model_dump(exclude_unset=True) == {
        "titulo": "Novo titulo",
        "estimativa": Estimativa.P,
        "bloco": Bloco.infra,
    }


def test_task_prioridade_normal_passa():
    body = TaskEdicao.model_validate({"prioridade": "alta"})

    assert body.prioridade is Prioridade.alta


# --------------------------------------------------------------------------
# nota: autor e task_id aceitam nulo; texto e resolvida nao
# --------------------------------------------------------------------------


@pytest.mark.parametrize("campo", ["texto", "resolvida"])
def test_nota_recusa_nulo_nos_campos_obrigatorios(campo):
    assert campo in recusa(NotaEdicao, {campo: None})


@pytest.mark.parametrize("campo", ["autor", "task_id"])
def test_nota_aceita_nulo_onde_ele_significa_soltar(campo):
    body = NotaEdicao.model_validate({campo: None})

    assert body.model_dump(exclude_unset=True) == {campo: None}


def test_nota_reabrir_passa():
    # `resolvida=false` reabre; e false, nao null.
    body = NotaEdicao.model_validate({"resolvida": False})

    assert body.model_dump(exclude_unset=True) == {"resolvida": False}


def test_a_mensagem_de_recusa_diz_quais_campos():
    mensagem = recusa(UsuarioEdicao, {"nome": None, "ativo": None})

    assert "ativo" in mensagem and "nome" in mensagem
