"""Template fixo das pre-tasks + o lint que decide se uma pre-task presta.

Tudo aqui e deterministico de proposito. A IA escreve o texto; este modulo
julga o texto sem depender do humor do modelo. Sao coisas mecanicamente
verificaveis: tamanho, enchimento, criterio de aceite, coerencia da
estimativa com o escopo descrito e duplicata.
"""

import difflib
import re

ESTIMATIVAS = ("PP", "P", "M", "G")
BLOCOS = ("frontend", "backend", "infra", "seguranca")

_ORDEM = {e: i for i, e in enumerate(ESTIMATIVAS)}

# Contrato devolvido para a IA junto com o conteudo do arquivo.
TEMPLATE_CONTRATO = """\
Cada pre-task DEVE ter exatamente estes campos:

  titulo      - imperativo, 6 a 80 chars, sem ponto final.
                Ruim: "Melhorias no login". Bom: "Validar expiracao do token no login".
  descricao   - 40 a 800 chars. Diga O QUE fazer e COMO saber que acabou.
                Termine com uma linha "Criterio de aceite: ...".
  estimativa  - PP (ate ~2h) | P (ate ~1 dia) | M (ate ~3 dias) | G (mais que isso).
                G e sinal de que talvez deva virar duas tasks.
  bloco       - frontend | backend | infra | seguranca

Proibido: "etc", "entre outros", "melhorias gerais", "diversos ajustes",
"e afins". Se nao souber o escopo, escreva menos, nao escreva vago.
Uma task = uma entrega verificavel. Nao agrupe assuntos diferentes.
"""

_ENCHIMENTO = [
    r"\betc\b", r"\bentre outros\b", r"\be afins\b", r"\bdiversos ajustes\b",
    r"\bmelhorias gerais\b", r"\bvarias melhorias\b", r"\bcoisas do tipo\b",
    r"\bdentre outras\b", r"\bse necessario\b", r"\bo que for preciso\b",
]

_TITULO_GENERICO = [
    r"^ajustes?$", r"^melhorias?$", r"^refatoracao$", r"^correcoes?$",
    r"^bugs?$", r"^tarefa\b", r"^task\b", r"^diversos$",
]

# Sinais de que o escopo e grande. Cada acerto conta 1.
_SINAIS_ESCOPO = [
    r"\bmigra(r|cao|ções|coes)\b", r"\bintegra(r|cao|coes)\b", r"\bautentica(r|cao)\b",
    r"\brefator(ar|acao)\b", r"\bredesenh(ar|o)\b", r"\breescrev(er|a)\b",
    r"\bmulti[- ]?tenant\b", r"\bpermiss(ao|oes)\b", r"\bcache\b", r"\bfila\b",
    r"\bwebsocket\b", r"\bdeploy\b", r"\bpipeline\b", r"\bcriptograf(ia|ar)\b",
    r"\bauditoria\b", r"\brollback\b", r"\bsharding\b", r"\bobservabilidade\b",
]


def _faixa_esperada(sinais: int) -> tuple[int, int]:
    if sinais <= 1:
        return _ORDEM["PP"], _ORDEM["P"]
    if sinais <= 3:
        return _ORDEM["P"], _ORDEM["M"]
    if sinais <= 5:
        return _ORDEM["M"], _ORDEM["G"]
    return _ORDEM["G"], _ORDEM["G"]


def contar_sinais_escopo(texto: str) -> int:
    baixo = texto.lower()
    sinais = sum(1 for p in _SINAIS_ESCOPO if re.search(p, baixo))
    # Cada item de lista na descricao tambem e um sinal de escopo.
    sinais += min(len(re.findall(r"^\s*[-*]\s+", texto, re.M)), 4)
    return sinais


def validar_pre_task(pre_task: dict, tasks_existentes: list[dict] | None = None) -> dict:
    """Devolve {veredito, motivos, sinais_escopo, estimativa_sugerida}."""
    motivos: list[str] = []
    titulo = (pre_task.get("titulo") or "").strip()
    descricao = (pre_task.get("descricao") or "").strip()
    estimativa = (pre_task.get("estimativa") or "").strip().upper()
    bloco = (pre_task.get("bloco") or "").strip().lower()

    # --- titulo ---
    if len(titulo) < 6:
        motivos.append("titulo muito curto (minimo 6 chars)")
    if len(titulo) > 80:
        motivos.append(f"titulo com {len(titulo)} chars (maximo 80)")
    if titulo.endswith("."):
        motivos.append("titulo nao deve terminar com ponto")
    if any(re.match(p, titulo.lower()) for p in _TITULO_GENERICO):
        motivos.append(f"titulo generico demais: '{titulo}' nao diz o que sera entregue")

    # --- descricao ---
    if len(descricao) < 40:
        motivos.append(f"descricao com {len(descricao)} chars (minimo 40); esta vaga")
    if len(descricao) > 800:
        motivos.append(f"descricao com {len(descricao)} chars (maximo 800); quebre a task")
    if "criterio de aceite" not in descricao.lower():
        motivos.append("falta a linha 'Criterio de aceite: ...' na descricao")

    # --- enchimento ---
    achados = {
        re.search(p, descricao.lower()).group(0)
        for p in _ENCHIMENTO
        if re.search(p, descricao.lower())
    }
    if achados:
        motivos.append(f"enchimento de linguica: {', '.join(sorted(achados))}")

    # --- enums ---
    if estimativa not in ESTIMATIVAS:
        motivos.append(f"estimativa '{estimativa}' invalida; use {'/'.join(ESTIMATIVAS)}")
    if bloco not in BLOCOS:
        motivos.append(f"bloco '{bloco}' invalido; use {'/'.join(BLOCOS)}")

    # --- coerencia estimativa x escopo ---
    sinais = contar_sinais_escopo(f"{titulo}\n{descricao}")
    lo, hi = _faixa_esperada(sinais)
    sugerida = ESTIMATIVAS[lo]
    if estimativa in ESTIMATIVAS:
        atual = _ORDEM[estimativa]
        if atual < lo:
            motivos.append(
                f"estimativa {estimativa} parece otimista: {sinais} sinais de escopo "
                f"no texto sugerem ao menos {ESTIMATIVAS[lo]}"
            )
        elif atual > hi:
            motivos.append(
                f"estimativa {estimativa} parece inflada: {sinais} sinais de escopo "
                f"sugerem no maximo {ESTIMATIVAS[hi]}"
            )

    # --- duplicata ---
    for existente in tasks_existentes or []:
        outro = (existente.get("titulo") or "").lower()
        if outro and difflib.SequenceMatcher(None, titulo.lower(), outro).ratio() > 0.8:
            motivos.append(
                f"parece duplicata da task #{existente.get('id')} '{existente.get('titulo')}'"
            )
            break

    return {
        "veredito": "aprovada" if not motivos else "precisa_de_ajuste",
        "motivos": motivos,
        "sinais_escopo": sinais,
        "estimativa_sugerida": sugerida,
    }
