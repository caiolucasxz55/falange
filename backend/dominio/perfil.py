"""Perfil do time: o que o Falange aprendeu com as escolhas de quem usa.

Modulo puro. Nao abre sessao, nao faz HTTP: recebe decisoes, preferencias e a
calibracao, e devolve o retrato.

O modelo nao aprende entre sessoes. Aqui as escolhas viram numero, o numero
vira frase, e a IA le a frase antes de agir. Nenhum limiar fica escondido em
prompt: estao todos logo abaixo.
"""

from collections import Counter
from typing import Any, Optional

# Abaixo de 5 vezes nao e padrao, e coincidencia.
MINIMO_OCORRENCIAS = 5

# Em 4 de 5 vezes a mesma escolha ja e um habito do time.
CONSISTENCIA_MINIMA = 0.8

# Campos cuja correcao humana vale aprender. Mudar titulo ou descricao e
# edicao de texto; mudar estes tres e discordar do julgamento da IA.
CAMPOS_AJUSTAVEIS = ("estimativa", "prioridade", "bloco")

# Ordem para saber se o humano subiu ou desceu o valor.
_ESCALAS = {
    "estimativa": ["PP", "P", "M", "G"],
    "prioridade": ["baixa", "media", "alta"],
}

# Frase pronta para os padroes que sabemos nomear. O resto cai no texto
# generico, para um padrao novo nunca passar despercebido.
_FRASES_PADRAO = {
    ("proxima_task", "destravar"): "o time escolhe destravar antes de pegar task nova",
    ("proxima_task", "prioritaria"): "o time escolhe sempre a mais prioritaria",
    ("proxima_task", "terminar"): "o time termina o que comecou antes de pegar outra",
    ("quebrar_task", "quebrar"): "o time prefere quebrar task G em duas",
    ("quebrar_task", "manter"): "o time prefere manter a task G inteira",
}


def _texto(valor: Any) -> Any:
    return getattr(valor, "value", valor)


def deve_registrar_ajuste(
    origem_task: Any, fonte: Optional[str], campos_alterados: dict
) -> bool:
    """A alteracao e um humano corrigindo a IA?

    Tres condicoes: a task foi escrita pela IA, a chamada NAO veio do MCP
    (o header `X-Falange-Fonte: mcp` identifica a propria IA mexendo) e o
    que mudou e campo de julgamento, nao de texto.
    """
    if _texto(origem_task) != "ia":
        return False
    if fonte == "mcp":
        return False
    return any(campo in CAMPOS_AJUSTAVEIS for campo in campos_alterados)


def _direcao(campo: str, antes: Any, depois: Any) -> str:
    """subiu, desceu ou trocou, conforme a escala do campo."""
    escala = _ESCALAS.get(campo)
    if not escala:
        return "trocou"
    try:
        return "subiu" if escala.index(depois) > escala.index(antes) else "desceu"
    except ValueError:
        return "trocou"


_VERBO = {
    "subiu": "aumentada",
    "desceu": "reduzida",
    "trocou": "trocada",
}


def _ajustes_comuns(decisoes: list[dict]) -> list[str]:
    """Frases do tipo "a estimativa da IA foi reduzida em 7 de 10 ajustes"."""
    por_campo: dict[str, Counter] = {}
    for decisao in decisoes:
        if _texto(decisao.get("tipo")) != "ajuste_humano":
            continue
        antes, depois = decisao.get("sugerido") or {}, decisao.get("escolhido") or {}
        for campo in CAMPOS_AJUSTAVEIS:
            if campo in depois and antes.get(campo) != depois.get(campo):
                direcao = _direcao(campo, antes.get(campo), depois.get(campo))
                por_campo.setdefault(campo, Counter())[direcao] += 1

    frases = []
    for campo, contagem in sorted(por_campo.items()):
        total = sum(contagem.values())
        direcao, vezes = contagem.most_common(1)[0]
        frases.append(
            f"a {campo} da IA foi {_VERBO[direcao]} em {vezes} de {total} ajustes"
        )
    return frases


def _rotulo(decisao: dict) -> Optional[str]:
    """Etiqueta curta da escolha, para agrupar decisoes comparaveis.

    Vem de `escolhido["rotulo"]`, que os comandos preenchem. No ajuste
    humano o rotulo e derivado: "estimativa_desceu", por exemplo.
    """
    escolhido = decisao.get("escolhido") or {}
    if _texto(decisao.get("tipo")) == "ajuste_humano":
        antes = decisao.get("sugerido") or {}
        for campo in CAMPOS_AJUSTAVEIS:
            if campo in escolhido and antes.get(campo) != escolhido.get(campo):
                return f"{campo}_{_direcao(campo, antes.get(campo), escolhido.get(campo))}"
        return None
    rotulo = escolhido.get("rotulo")
    return str(rotulo) if rotulo else None


def _padroes_candidatos(decisoes: list[dict], preferencias: list[dict]) -> list[dict]:
    """Habitos que ja aparecem nos dados mas ninguem confirmou ainda.

    Regra, deterministica: agrupa por tipo de decisao, olha o rotulo mais
    escolhido e aceita quando houve ao menos MINIMO_OCORRENCIAS decisoes
    daquele tipo e o rotulo campeao responde por CONSISTENCIA_MINIMA delas.
    Padrao cuja frase ja virou preferencia (ativa ou nao) fica de fora: nao
    se pergunta duas vezes a mesma coisa.
    """
    ja_conhecidas = {(p.get("descricao") or "").strip() for p in preferencias}

    por_tipo: dict[str, list[str]] = {}
    for decisao in decisoes:
        rotulo = _rotulo(decisao)
        if rotulo:
            por_tipo.setdefault(_texto(decisao.get("tipo")), []).append(rotulo)

    candidatos = []
    for tipo, rotulos in sorted(por_tipo.items()):
        total = len(rotulos)
        if total < MINIMO_OCORRENCIAS:
            continue
        rotulo, vezes = Counter(rotulos).most_common(1)[0]
        consistencia = vezes / total
        if consistencia < CONSISTENCIA_MINIMA:
            continue

        descricao = _FRASES_PADRAO.get(
            (tipo, rotulo), f"em {tipo}, o time escolhe '{rotulo}'"
        )
        if descricao in ja_conhecidas:
            continue
        candidatos.append(
            {
                "descricao": descricao,
                "tipo": tipo,
                "rotulo": rotulo,
                "ocorrencias": vezes,
                "total": total,
                "consistencia": round(consistencia, 2),
            }
        )
    return candidatos


def montar(
    decisoes: list[dict],
    preferencias: list[dict],
    calibracao: Optional[dict] = None,
) -> dict:
    """Retrato do time: aceitacao, correcoes, preferencias e candidatos."""
    aceitacao: dict[str, dict] = {}
    for decisao in decisoes:
        tipo = _texto(decisao.get("tipo"))
        linha = aceitacao.setdefault(tipo, {"n": 0, "aceitas": 0, "taxa": 0.0})
        linha["n"] += 1
        if decisao.get("aceita"):
            linha["aceitas"] += 1
    for linha in aceitacao.values():
        linha["taxa"] = round(linha["aceitas"] / linha["n"], 2)

    return {
        "calibracao": calibracao,
        "aceitacao_por_tipo": dict(sorted(aceitacao.items())),
        "ajustes_comuns": _ajustes_comuns(decisoes),
        "preferencias_ativas": [p for p in preferencias if p.get("ativa")],
        "padroes_candidatos": _padroes_candidatos(decisoes, preferencias),
        "minimo_ocorrencias": MINIMO_OCORRENCIAS,
        "consistencia_minima": CONSISTENCIA_MINIMA,
    }
