"""Testes do lint de pre-tasks. E puro: nao precisa de banco nem de backend.

O foco e o tratamento de acento, que reprovava texto escrito corretamente
em portugues.
"""

from falange_mcp.template import validar_pre_task

BOA_DESCRICAO = (
    "Percorrer a cadeia de bloqueio e recusar com 409 quando o alvo levar de "
    "volta a propria task.\n"
    "Critério de aceite: com A travando B, travar A por B retorna 409."
)


def test_criterio_de_aceite_com_acento_e_aprovada():
    veredito = validar_pre_task(
        {
            "titulo": "Recusar ciclo de bloqueio ao definir dependencia",
            "descricao": BOA_DESCRICAO,
            "estimativa": "P",
            "bloco": "backend",
        }
    )
    assert veredito["veredito"] == "aprovada", veredito["motivos"]


def test_enchimento_com_acento_e_reprovado():
    veredito = validar_pre_task(
        {
            "titulo": "Ajustar importacao de CSV do Jira",
            "descricao": (
                "Revisar o importador e tratar as linhas invalidas se necessário.\n"
                "Critério de aceite: a importacao termina sem derrubar o processo."
            ),
            "estimativa": "P",
            "bloco": "backend",
        }
    )
    assert veredito["veredito"] == "precisa_de_ajuste"
    assert any("enchimento de linguica" in m for m in veredito["motivos"])
    # A mensagem mostra o trecho como foi escrito, com acento.
    assert any("se necessário" in m for m in veredito["motivos"])


def test_titulo_generico_com_acento_e_reprovado():
    veredito = validar_pre_task(
        {
            "titulo": "Refatoração",
            "descricao": BOA_DESCRICAO,
            "estimativa": "P",
            "bloco": "backend",
        }
    )
    assert veredito["veredito"] == "precisa_de_ajuste"
    assert any("generico" in m for m in veredito["motivos"])


def test_duplicata_detectada_apesar_do_acento():
    # Titulo curto e denso em acento: sem normalizar, a similaridade fica em
    # 0.79 e passa despercebida; normalizado, os dois titulos sao iguais.
    veredito = validar_pre_task(
        {
            "titulo": "Validação de sessão órfã",
            "descricao": BOA_DESCRICAO,
            "estimativa": "P",
            "bloco": "backend",
        },
        tasks_existentes=[{"id": 7, "titulo": "Validacao de sessao orfa"}],
    )
    assert veredito["veredito"] == "precisa_de_ajuste"
    assert any("duplicata da task #7" in m for m in veredito["motivos"])


def test_prioridade_invalida_e_reprovada():
    veredito = validar_pre_task(
        {
            "titulo": "Recusar ciclo de bloqueio ao definir dependencia",
            "descricao": BOA_DESCRICAO,
            "estimativa": "P",
            "bloco": "backend",
            "prioridade": "urgentissima",
        }
    )
    assert veredito["veredito"] == "precisa_de_ajuste"
    assert any("prioridade 'urgentissima' invalida" in m for m in veredito["motivos"])


def test_prioridade_ausente_vale_media():
    veredito = validar_pre_task(
        {
            "titulo": "Recusar ciclo de bloqueio ao definir dependencia",
            "descricao": BOA_DESCRICAO,
            "estimativa": "P",
            "bloco": "backend",
        }
    )
    assert veredito["veredito"] == "aprovada", veredito["motivos"]


def test_bloco_e_prioridade_com_acento_sao_aceitos():
    veredito = validar_pre_task(
        {
            "titulo": "Restringir origens do CORS por ambiente",
            "descricao": BOA_DESCRICAO,
            "estimativa": "P",
            "bloco": "segurança",
            "prioridade": "média",
        }
    )
    assert veredito["veredito"] == "aprovada", veredito["motivos"]
