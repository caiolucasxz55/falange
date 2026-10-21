"""Template fixo das pre-tasks + o lint que decide se uma pre-task presta.

Tudo aqui e deterministico de proposito. A IA escreve o texto; este modulo
julga o texto sem depender do humor do modelo. Sao coisas mecanicamente
verificaveis: tamanho, enchimento, criterio de aceite, coerencia da
estimativa com o escopo descrito e duplicata.
"""

import difflib
import re
import unicodedata

ESTIMATIVAS = ("PP", "P", "M", "G")
BLOCOS = ("frontend", "backend", "infra", "seguranca")
STATUS = ("aberta", "em_andamento", "concluida")
PRIORIDADES = ("alta", "media", "baixa")
# Espelham os enums do backend; o MCP nao importa nada de backend/.
TIPOS_DECISAO = (
    "proxima_task", "prioridade", "estimativa", "quebrar_task", "pre_task",
)
ORIGENS_PREFERENCIA = ("explicita", "inferida")
TIPOS_ACAO = (
    "definir_prioridade", "definir_estimativa", "marcar_bloqueio",
    "criar_pre_tasks_aprovadas",
)
NIVEIS_AUTONOMIA = ("perguntar", "confirmar_em_lote", "automatico")

_ORDEM = {e: i for i, e in enumerate(ESTIMATIVAS)}

# De 1 a 5 criterios por task, 10 a 200 chars cada. Espelham
# `backend/models/criterio.py`; o MCP nao importa nada de backend/.
MIN_CRITERIOS, MAX_CRITERIOS = 1, 5
MIN_TEXTO_CRITERIO, MAX_TEXTO_CRITERIO = 10, 200

# Contrato devolvido para a IA junto com o conteudo do arquivo.
TEMPLATE_CONTRATO = """\
Cada pre-task DEVE ter exatamente estes campos:

  titulo      - imperativo, 6 a 80 chars, sem ponto final.
                Ruim: "Melhorias no login". Bom: "Validar expiracao do token no login".
  descricao   - 40 a 800 chars. Diga O QUE fazer e POR QUE.
  criterios   - lista de 1 a 5 textos, 10 a 200 chars cada: como se SABE que
                acabou. Cada um tem de ser observavel -- algo que da para
                olhar e dizer "cumpriu" ou "nao cumpriu".
                Ruim: "funcionar bem", "o codigo fica mais limpo".
                Bom: "o login com token vencido retorna 401",
                     "a task bloqueada nao aparece em sugerir_proximas".
                Cinco criterios e o teto: task que precisa de seis sao duas.
  estimativa  - PP (ate ~2h) | P (ate ~1 dia) | M (ate ~3 dias) | G (mais que isso).
                G e sinal de que talvez deva virar duas tasks.
  bloco       - frontend | backend | infra | seguranca
  prioridade  - alta  (bloqueia outras tasks ou e pre-requisito de uma
                       entrega proxima)
                media (padrao; na duvida, e media)
                baixa (pode esperar sem travar ninguem)

Nao marque tudo como alta: se tudo e prioridade, nada e.

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


def normalizar(texto: str) -> str:
    """Minusculas e sem acento: os padroes deste modulo sao escritos sem acento,
    entao "Criterio" e "Criterio de aceite" precisam casar com "Critério"."""
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _faixa_esperada(sinais: int) -> tuple[int, int]:
    if sinais <= 1:
        return _ORDEM["PP"], _ORDEM["P"]
    if sinais <= 3:
        return _ORDEM["P"], _ORDEM["M"]
    if sinais <= 5:
        return _ORDEM["M"], _ORDEM["G"]
    return _ORDEM["G"], _ORDEM["G"]


def contar_sinais_escopo(texto: str) -> int:
    baixo = normalizar(texto)
    sinais = sum(1 for p in _SINAIS_ESCOPO if re.search(p, baixo))
    # Cada item de lista na descricao tambem e um sinal de escopo.
    sinais += min(len(re.findall(r"^\s*[-*]\s+", texto, re.M)), 4)
    return sinais


# Intencao disfarcada de criterio: promete uma qualidade, nao um fato que da
# para observar. "Funcionar bem" nao e verificavel -- nunca se sabe se
# cumpriu.
_INTENCAO = [
    r"\bfuncionar?\b", r"\bfuncionando\b", r"\bcorretamente\b",
    r"\badequadamente\b", r"\bmelhor(ar|ia|ado)?\b", r"\botimiz(ar|ado)\b",
    r"\bmais (rapido|limpo|simples|organizado|facil)\b",
    r"\bfica(r)? (bom|melhor|legal|pronto)\b", r"\bsem (bugs?|problemas?)\b",
    r"\bbem feito\b", r"\bde forma (eficiente|correta|adequada)\b",
    r"\bperformance\b", r"\bqualidade do codigo\b",
]

# Um criterio observavel aponta para algo que se olha: um verbo de
# observacao, um numero (409, 15 minutos, 2 replicas) ou um identificador
# tecnico (/tasks, TaskOut, X-Falange-Fonte).
_VERBOS_OBSERVAVEIS = [
    r"\bretorna\b", r"\bdevolve\b", r"\bresponde\b", r"\brecusa\b",
    r"\baceita\b", r"\baparece\b", r"\bexibe\b", r"\bmostra\b",
    r"\bsome\b", r"\bnao aparece\b", r"\bgrava\b", r"\bguarda\b",
    r"\bcria\b", r"\bapaga\b", r"\bremove\b", r"\bredireciona\b",
    r"\bbloqueia\b", r"\bdestrava\b", r"\bpassa\b", r"\bfalha\b",
    r"\bregistra\b", r"\bconta\b", r"\blista\b", r"\bmarca\b",
    r"\bcontinua\b", r"\bdeixa de\b", r"\bpermanece\b", r"\bvolta\b",
    r"\bcarrega\b", r"\babre\b", r"\bfecha\b", r"\bavisa\b",
]
_TECNICO = [r"\d", r"/[a-z]", r"[a-z]_[a-z]", r"[a-z][A-Z]", r"\b[A-Z]{2,}\b"]

_MARCADOR_CRITERIO = re.compile(r"criterios?\s+de\s+aceite\s*:?\s*", re.I)
_BULLET = re.compile(r"^\s*[-*]\s+", re.M)


def extrair_criterios(descricao: str) -> list[str]:
    """Os criterios escritos na descricao, no formato antigo de uma linha.

    Existe para compatibilidade: antes da tabela `criterio`, o criterio de
    aceite era uma linha dentro da descricao, e e isso que `/falange-gerar`
    ainda produz. Reproduz a extracao da migration 0010 -- as duas leem o
    mesmo formato, uma no banco e outra na pre-task.
    """
    if not descricao:
        return []
    sem_acento = normalizar(descricao)
    achado = _MARCADOR_CRITERIO.search(sem_acento)
    # Sem alinhamento de indices nao da para cortar no texto original, e
    # devolver o normalizado perderia o acento de quem escreveu.
    if not achado or len(sem_acento) != len(descricao):
        return []

    resto = descricao[achado.end():].strip()
    if not resto:
        return []
    if _BULLET.search(resto):
        brutos = [_BULLET.sub("", linha).strip() for linha in resto.splitlines()]
    else:
        brutos = [" ".join(resto.split())]
    return [b for b in brutos if b][:MAX_CRITERIOS]


def validar_criterios(criterios: list[str]) -> list[str]:
    """Motivos para recusar esta lista de criterios. Vazia = aprovada.

    So julga o que e mecanicamente verificavel: quantidade, tamanho,
    repeticao, enchimento, promessa de intencao e ausencia de qualquer sinal
    observavel. Nao tenta adivinhar se o criterio e o CERTO para a task --
    isso e do dev.
    """
    motivos: list[str] = []
    if len(criterios) < MIN_CRITERIOS:
        return ["falta criterio de aceite: mande ao menos 1 (como se sabe que acabou)"]
    if len(criterios) > MAX_CRITERIOS:
        motivos.append(
            f"{len(criterios)} criterios (no maximo {MAX_CRITERIOS}); "
            "task que precisa de mais sao duas tasks"
        )

    vistos: dict[str, int] = {}
    for i, bruto in enumerate(criterios[:MAX_CRITERIOS], start=1):
        texto = (bruto or "").strip()
        baixo = normalizar(texto)
        rotulo = f"criterio {i}"

        if len(texto) < MIN_TEXTO_CRITERIO:
            motivos.append(
                f"{rotulo} muito curto (minimo {MIN_TEXTO_CRITERIO} chars): '{texto}'"
            )
            # Sem texto nao ha o que julgar depois; evita empilhar motivos
            # sobre a mesma falta.
            continue
        if len(texto) > MAX_TEXTO_CRITERIO:
            motivos.append(
                f"{rotulo} com {len(texto)} chars (maximo {MAX_TEXTO_CRITERIO}); "
                "isso e descricao, nao criterio"
            )

        if baixo in vistos:
            motivos.append(f"{rotulo} repetido (igual ao {vistos[baixo]})")
        else:
            vistos[baixo] = i

        enchimento = {
            re.search(p, baixo).group(0) for p in _ENCHIMENTO if re.search(p, baixo)
        }
        if enchimento:
            motivos.append(
                f"{rotulo} com enchimento de linguica: {', '.join(sorted(enchimento))}"
            )

        intencao = {
            re.search(p, baixo).group(0) for p in _INTENCAO if re.search(p, baixo)
        }
        if intencao:
            motivos.append(
                f"{rotulo} promete intencao, nao fato ({', '.join(sorted(intencao))}): "
                f"'{texto}' -- diga o que da para OBSERVAR"
            )
        elif not any(re.search(p, baixo) for p in _VERBOS_OBSERVAVEIS) and not any(
            re.search(p, texto) for p in _TECNICO
        ):
            motivos.append(
                f"{rotulo} nao diz nada observavel: '{texto}' -- o que se olha "
                "para saber que cumpriu?"
            )

    return motivos


def validar_pre_task(pre_task: dict, tasks_existentes: list[dict] | None = None) -> dict:
    """Devolve {veredito, motivos, sinais_escopo, estimativa_sugerida}."""
    motivos: list[str] = []
    titulo = (pre_task.get("titulo") or "").strip()
    descricao = (pre_task.get("descricao") or "").strip()
    # Sem acento e sem caixa: "Seguranca" e "seguranca" sao o mesmo bloco.
    estimativa = normalizar(pre_task.get("estimativa") or "").upper()
    bloco = normalizar(pre_task.get("bloco") or "")
    # Prioridade e opcional: ausente vale media, como no backend.
    prioridade = normalizar(pre_task.get("prioridade") or "media")
    titulo_norm = normalizar(titulo)
    descricao_norm = normalizar(descricao)

    # --- titulo ---
    if len(titulo) < 6:
        motivos.append("titulo muito curto (minimo 6 chars)")
    if len(titulo) > 80:
        motivos.append(f"titulo com {len(titulo)} chars (maximo 80)")
    if titulo.endswith("."):
        motivos.append("titulo nao deve terminar com ponto")
    if any(re.match(p, titulo_norm) for p in _TITULO_GENERICO):
        motivos.append(f"titulo generico demais: '{titulo}' nao diz o que sera entregue")

    # --- descricao ---
    if len(descricao) < 40:
        motivos.append(f"descricao com {len(descricao)} chars (minimo 40); esta vaga")
    if len(descricao) > 800:
        motivos.append(f"descricao com {len(descricao)} chars (maximo 800); quebre a task")

    # --- criterios de aceite ---
    # A lista e o contrato. Quando ela nao vem, o criterio e procurado na
    # descricao, no formato antigo de uma linha: `/falange-gerar` ainda
    # produz assim, e reprovar por isso quebraria o comando sem ganhar nada.
    criterios = [
        str(c).strip() for c in (pre_task.get("criterios") or []) if str(c).strip()
    ]
    if not criterios:
        criterios = extrair_criterios(descricao)
    motivos.extend(validar_criterios(criterios))

    # --- enchimento ---
    achados = set()
    for padrao in _ENCHIMENTO:
        achado = re.search(padrao, descricao_norm)
        if achado:
            # Mostra o trecho como o usuario escreveu. NFKD preserva o numero de
            # caracteres para acento latino; se nao preservar, cai no normalizado.
            inicio, fim = achado.span()
            alinhado = len(descricao_norm) == len(descricao)
            achados.add(descricao[inicio:fim] if alinhado else achado.group(0))
    if achados:
        motivos.append(f"enchimento de linguica: {', '.join(sorted(achados))}")

    # --- enums ---
    if estimativa not in ESTIMATIVAS:
        motivos.append(f"estimativa '{estimativa}' invalida; use {'/'.join(ESTIMATIVAS)}")
    if bloco not in BLOCOS:
        motivos.append(f"bloco '{bloco}' invalido; use {'/'.join(BLOCOS)}")
    if prioridade not in PRIORIDADES:
        motivos.append(
            f"prioridade '{prioridade}' invalida; use {'/'.join(PRIORIDADES)}"
        )

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
        outro = normalizar(existente.get("titulo") or "")
        if outro and difflib.SequenceMatcher(None, titulo_norm, outro).ratio() > 0.8:
            motivos.append(
                f"parece duplicata da task #{existente.get('id')} '{existente.get('titulo')}'"
            )
            break

    return {
        "veredito": "aprovada" if not motivos else "precisa_de_ajuste",
        "motivos": motivos,
        "criterios": criterios,
        "sinais_escopo": sinais,
        "estimativa_sugerida": sugerida,
    }
