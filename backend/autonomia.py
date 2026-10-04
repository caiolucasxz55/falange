"""Autonomia por tipo de acao: quanto a IA pode fazer sem perguntar.

Modulo puro. Nao abre sessao, nao faz HTTP.

A confianca sobe devagar e cai na hora. Subir exige um historico limpo E um
humano dizendo sim; descer acontece sozinho, na primeira discordancia. A
assimetria e de proposito: o custo de uma promocao errada e maior que o de
uma demora em promover.
"""

from typing import Any, Optional

# Decisoes seguidas, todas aceitas, para a promocao ficar disponivel.
JANELA = 5

# Do menos para o mais autonomo. A ordem e a escada de promocao.
NIVEIS = ("perguntar", "confirmar_em_lote", "automatico")

# As quatro acoes que podem ganhar autonomia.
#
# Apagar task e apagar nota NAO estao aqui de proposito, e nao devem entrar:
# acao destrutiva nunca fica automatica, por melhor que seja o historico.
ACOES = (
    "definir_prioridade",
    "definir_estimativa",
    "marcar_bloqueio",
    "criar_pre_tasks_aprovadas",
)

# Que tipo de decisao alimenta cada acao. `marcar_bloqueio` nao tem um tipo
# de decisao proprio hoje, entao nunca acumula historico e nunca promove.
DECISAO_POR_ACAO: dict[str, Optional[str]] = {
    "definir_prioridade": "prioridade",
    "definir_estimativa": "estimativa",
    "marcar_bloqueio": None,
    "criar_pre_tasks_aprovadas": "pre_task",
}

# Campo corrigido pelo humano -> acao que perde confianca por causa disso.
ACAO_POR_CAMPO = {
    "prioridade": "definir_prioridade",
    "estimativa": "definir_estimativa",
}


def _texto(valor: Any) -> Any:
    return getattr(valor, "value", valor)


def proximo_nivel(nivel_atual: str) -> Optional[str]:
    """O degrau acima, ou None se ja esta no topo."""
    try:
        indice = NIVEIS.index(nivel_atual)
    except ValueError:
        return None
    return NIVEIS[indice + 1] if indice + 1 < len(NIVEIS) else None


def pode_promover(
    decisoes_do_tipo: list[dict], nivel_atual: str = "perguntar"
) -> dict:
    """A acao ja merece subir um degrau?

    `decisoes_do_tipo` vem das mais recentes para as mais antigas. Exige
    JANELA decisoes seguidas, todas aceitas. Uma recusa no meio zera.

    Devolve {"pode", "proximo_nivel", "aceitas_seguidas", "motivo"}. Mesmo
    com True, a promocao so acontece com um sim explicito do dev.
    """
    acima = proximo_nivel(nivel_atual)
    janela = decisoes_do_tipo[:JANELA]
    seguidas = 0
    for decisao in janela:
        if not decisao.get("aceita"):
            break
        seguidas += 1

    if acima is None:
        motivo = f"ja esta em {nivel_atual}, o nivel mais autonomo"
    elif len(janela) < JANELA:
        motivo = f"historico curto: {len(janela)} de {JANELA} decisoes"
    elif seguidas < JANELA:
        motivo = f"houve recusa nas ultimas {JANELA}: {seguidas} aceitas seguidas"
    else:
        motivo = f"as ultimas {JANELA} decisoes foram aceitas sem ajuste"

    return {
        "pode": acima is not None and seguidas >= JANELA,
        "proximo_nivel": acima,
        "aceitas_seguidas": seguidas,
        "motivo": motivo,
    }


def acoes_a_rebaixar(decisao: dict, niveis: dict[str, str]) -> dict[str, str]:
    """Que acoes perdem autonomia por causa desta decisao.

    Rebaixa so o que estava em `automatico`: discordar de algo que a IA fez
    sozinha e o sinal de que ela nao devia estar fazendo sozinha. Nos niveis
    de baixo o humano ja estava no circuito, entao recusar e o fluxo normal.

    Devolve {acao: novo_nivel}, vazio quando nada muda.
    """
    tipo = _texto(decisao.get("tipo"))
    discordou = tipo == "ajuste_humano" or not decisao.get("aceita")
    if not discordou:
        return {}

    if tipo == "ajuste_humano":
        campos = (decisao.get("escolhido") or {}).keys()
        alvos = {ACAO_POR_CAMPO[c] for c in campos if c in ACAO_POR_CAMPO}
    else:
        alvos = {a for a, t in DECISAO_POR_ACAO.items() if t == tipo}

    abaixo = NIVEIS[NIVEIS.index("automatico") - 1]
    return {
        acao: abaixo for acao in sorted(alvos) if niveis.get(acao) == "automatico"
    }


def montar(niveis: dict[str, str], decisoes_por_tipo: dict[str, list[dict]]) -> dict:
    """Retrato da autonomia: nivel atual e situacao de promocao por acao."""
    saida = {}
    for acao in ACOES:
        nivel = niveis.get(acao, NIVEIS[0])
        tipo = DECISAO_POR_ACAO[acao]
        decisoes = decisoes_por_tipo.get(tipo, []) if tipo else []
        saida[acao] = {"nivel": nivel, **pode_promover(decisoes, nivel)}
    return {"acoes": saida, "janela": JANELA, "niveis": list(NIVEIS)}
