"""Testes do motor de priorizacao. Modulo puro: nao precisa de banco."""

from datetime import datetime, timedelta, timezone
from enum import Enum

from backend.priorizacao import PESOS, ranquear

AGORA = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)


def task(id, **campos):
    """Task com os campos que o motor le; o resto vem do padrao."""
    base = {
        "id": id,
        "titulo": f"Task {id}",
        "descricao": "",
        "estimativa": "P",
        "bloco": "backend",
        "prioridade": "media",
        "responsavel": None,
        "bloqueada_por": None,
        "status": "aberta",
        "criada_em": AGORA,
        "iniciada_em": None,
        "concluida_em": None,
    }
    base.update(campos)
    return base


def por_id(resultado):
    return {s["id"]: s for s in resultado["sugestoes"]}


def tipos(resultado):
    return [a["tipo"] for a in resultado["alertas"]]


def test_destravamento_conta_a_cadeia_transitiva():
    # 1 trava 2, 2 trava 3: a 1 destrava duas tasks, nao uma.
    tasks = [task(1), task(2, bloqueada_por=1), task(3, bloqueada_por=2)]

    saida = ranquear(tasks, AGORA)
    primeira = por_id(saida)[1]

    assert primeira["destrava"] == [2, 3]
    assert any("destrava 2 tasks (#2, #3)" in m for m in primeira["motivos"])
    assert primeira["score"] == PESOS["prioridade_media"] + 2 * PESOS["destrava_por_task"]


def test_tetos_de_destravamento_e_idade_sao_respeitados():
    # 6 dependentes diretos passariam de 60, mas o teto e 40.
    tasks = [task(1, prioridade="baixa", criada_em=AGORA - timedelta(days=90))]
    tasks += [task(i, bloqueada_por=1) for i in range(2, 8)]

    primeira = por_id(ranquear(tasks, AGORA))[1]

    assert primeira["score"] == PESOS["destrava_teto"] + PESOS["idade_teto"]


def test_task_bloqueada_fica_fora_das_sugestoes():
    tasks = [task(1), task(2, bloqueada_por=1), task(3, status="concluida")]

    sugeridas = por_id(ranquear(tasks, AGORA))

    assert set(sugeridas) == {1}


def test_task_em_andamento_da_pessoa_vem_primeiro():
    # A 2 tem score maior, mas a 1 ja esta comecada por quem perguntou.
    tasks = [
        task(1, responsavel="caio", status="em_andamento", iniciada_em=AGORA),
        task(2, prioridade="alta"),
    ]

    saida = ranquear(tasks, AGORA, responsavel="caio")

    assert [s["id"] for s in saida["sugestoes"]] == [1, 2]
    assert saida["sugestoes"][0]["score"] < saida["sugestoes"][1]["score"]
    assert "termine antes de comecar" in saida["sugestoes"][0]["motivos"]


def test_sem_responsavel_a_ordem_segue_o_score():
    tasks = [
        task(1, responsavel="caio", status="em_andamento", iniciada_em=AGORA),
        task(2, prioridade="alta"),
    ]

    assert [s["id"] for s in ranquear(tasks, AGORA)["sugestoes"]] == [2, 1]


def test_desempate_por_id():
    tasks = [task(3), task(1), task(2)]

    assert [s["id"] for s in ranquear(tasks, AGORA)["sugestoes"]] == [1, 2, 3]


def test_alerta_de_inversao_aponta_a_alta_travada():
    # A 1 e baixa mas trava a 3 (alta), por tabela, via 2.
    tasks = [
        task(1, prioridade="baixa"),
        task(2, bloqueada_por=1),
        task(3, prioridade="alta", bloqueada_por=2),
    ]

    inversoes = [a for a in ranquear(tasks, AGORA)["alertas"] if a["tipo"] == "inversao"]

    # As duas travam a alta: a 1 por tabela e a 2 diretamente.
    assert {a["task_id"] for a in inversoes} == {1, 2}
    por_task = {a["task_id"]: a for a in inversoes}
    assert por_task[1]["tasks_afetadas"] == [3]
    assert "#3" in por_task[1]["mensagem"] and "baixa" in por_task[1]["mensagem"]


def test_inversao_ignora_quem_nao_trava_alta():
    tasks = [task(1, prioridade="baixa"), task(2, prioridade="media", bloqueada_por=1)]

    assert "inversao" not in tipos(ranquear(tasks, AGORA))


def test_alerta_de_inflacao_so_acima_do_limite():
    # 2 de 5 = 40%, no limite e ainda aceitavel.
    no_limite = [task(i, prioridade="alta") for i in (1, 2)]
    no_limite += [task(i) for i in (3, 4, 5)]
    assert "inflacao" not in tipos(ranquear(no_limite, AGORA))

    # 3 de 5 = 60%, passou.
    acima = [task(i, prioridade="alta") for i in (1, 2, 3)]
    acima += [task(i) for i in (4, 5)]
    assert "inflacao" in tipos(ranquear(acima, AGORA))


def test_alerta_de_parada_so_depois_de_cinco_dias():
    recente = [
        task(1, status="em_andamento", iniciada_em=AGORA - timedelta(days=5)),
    ]
    assert "parada" not in tipos(ranquear(recente, AGORA))

    antiga = [
        task(1, status="em_andamento", iniciada_em=AGORA - timedelta(days=6)),
    ]
    alerta = [a for a in ranquear(antiga, AGORA)["alertas"] if a["tipo"] == "parada"]
    assert alerta and "6 dias" in alerta[0]["mensagem"]


def test_sobrecarga_vira_aviso_sem_mexer_no_score():
    tasks = [task(1, responsavel="caio")]
    cargas = {"caio": {"tasks_abertas": 9, "limite": 5, "sobrecarregado": True}}

    sem = ranquear(tasks, AGORA, responsavel="caio")
    com = ranquear(tasks, AGORA, cargas=cargas, responsavel="caio")

    assert com["avisos"] and "9 tasks abertas" in com["avisos"][0]
    assert sem["avisos"] == []
    assert com["sugestoes"][0]["score"] == sem["sugestoes"][0]["score"]


class PrioridadeFalsa(str, Enum):
    """Imita o enum do ORM, que chega pelo model_dump sem virar string."""

    alta = "alta"
    media = "media"


def test_enum_do_orm_nao_perde_o_peso_da_prioridade():
    # Enum de str compara igual a "media", mas quebra como chave de PESOS.
    tasks = [task(1, prioridade=PrioridadeFalsa.media)]

    saida = ranquear(tasks, AGORA)["sugestoes"][0]

    assert saida["score"] == PESOS["prioridade_media"]
    assert "prioridade media" in saida["motivos"]
    assert saida["prioridade"] == "media"
