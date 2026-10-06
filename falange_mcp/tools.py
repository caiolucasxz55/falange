"""Logica das tools do Falange.

Este modulo NAO sabe o que e stdio ou SSE. Nenhum import de transporte,
nenhum decorator de servidor. Sao funcoes Python comuns -- o que permite
testar cada uma sem subir servidor nenhum.

Regra: as tools falam com o backend por HTTP. Nunca com o Postgres direto.
"""

import os
import re
from pathlib import Path

import httpx

from falange_mcp.config import settings
from falange_mcp.template import (
    BLOCOS,
    ESTIMATIVAS,
    NIVEIS_AUTONOMIA,
    ORIGENS_PREFERENCIA,
    PRIORIDADES,
    STATUS,
    TEMPLATE_CONTRATO,
    TIPOS_ACAO,
    TIPOS_DECISAO,
    normalizar,
    validar_pre_task,
)

BACKEND = settings.backend_url

EXTENSOES_OK = {
    ".md", ".txt", ".rst", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".json", ".yaml", ".yml", ".toml", ".sql", ".sh",
}
MAX_CHARS = 20_000
MAX_CHARS_PASTA = 60_000

# Pastas que nunca interessam: dependencia, build e lixo de ferramenta.
PASTAS_IGNORADAS = {
    ".git", "node_modules", ".venv", "__pycache__", ".next", "dist", "build",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
}

# Documentacao primeiro, codigo depois: a IA le o "porque" antes do "como".
EXTENSOES_DOC = {".md", ".rst", ".txt"}


def _erro_422(corpo: dict) -> str:
    """Traduz o 422 do FastAPI em uma frase acionavel."""
    partes = []
    for item in corpo.get("detail", []):
        campo = ".".join(str(x) for x in item.get("loc", []) if x != "body")
        partes.append(f"{campo}: {item.get('msg', 'invalido')}")
    return "; ".join(partes) or "payload invalido"


# O backend usa isto para saber que quem chamou foi a IA. Sem o header, a
# alteracao conta como correcao humana e vira aprendizado.
CABECALHO_FONTE = {"X-Falange-Fonte": "mcp"}


def _pedir(metodo: str, caminho: str, **kw):
    """Chama o backend e NUNCA levanta: devolve o json ou {'erro': <frase>}.

    Uma excecao vira 'Error executing tool X' do lado do client MCP, o que
    nao diz nada para a IA. Um dict com 'erro' ela consegue ler e corrigir.
    """
    try:
        cabecalhos = {**CABECALHO_FONTE, **(kw.pop("headers", None) or {})}
        if settings.api_token:
            cabecalhos["Authorization"] = f"Bearer {settings.api_token}"
        r = httpx.request(
            metodo, f"{BACKEND}{caminho}", timeout=10, headers=cabecalhos, **kw
        )
    except httpx.HTTPError as e:
        return {"erro": f"backend inacessivel em {BACKEND}: {e}"}

    if r.status_code == 401:
        return {"erro": "backend recusou o token (FALANGE API_TOKEN confere?)"}
    if r.status_code == 204:
        return {"ok": True}
    if r.status_code == 422:
        return {"erro": _erro_422(r.json())}
    if r.status_code >= 400:
        try:
            return {"erro": str(r.json().get("detail", r.text))}
        except Exception:
            return {"erro": f"HTTP {r.status_code}: {r.text[:200]}"}
    return r.json()


# Campos femininos, para a mensagem de erro concordar.
_CAMPOS_FEMININOS = {"estimativa", "prioridade"}


def _canonizar(valor: str | None, validos: tuple[str, ...]) -> str | None:
    """Casa o valor com a opcao oficial ignorando acento e caixa.

    "Seguranca", "SEGURANCA" e "seguranca" chegam como o mesmo bloco. Valor
    que nao casa volta como veio, para a mensagem de erro citar o original.
    """
    if valor is None:
        return None
    alvo = normalizar(valor.strip())
    for oficial in validos:
        if normalizar(oficial) == alvo:
            return oficial
    return valor


def _checar(valor, validos, campo: str) -> str | None:
    if valor is not None and valor not in validos:
        genero = "invalida" if campo in _CAMPOS_FEMININOS else "invalido"
        return f"{campo} '{valor}' {genero}; use {'/'.join(validos)}"
    return None


# --------------------------------------------------------------------------
# tools que so repassam para o backend
# --------------------------------------------------------------------------

def criar_task(
    titulo: str,
    estimativa: str,
    bloco: str,
    descricao: str = "",
    prioridade: str = "media",
    responsavel: str | None = None,
) -> dict:
    """Cria uma task. estimativa: PP/P/M/G. bloco: frontend/backend/infra/seguranca.

    prioridade: alta/media/baixa (padrao media).
    """
    estimativa = _canonizar(estimativa, ESTIMATIVAS)
    bloco = _canonizar(bloco, BLOCOS)
    prioridade = _canonizar(prioridade, PRIORIDADES)
    for erro in (
        _checar(estimativa, ESTIMATIVAS, "estimativa"),
        _checar(bloco, BLOCOS, "bloco"),
        _checar(prioridade, PRIORIDADES, "prioridade"),
    ):
        if erro:
            return {"erro": erro}

    return _pedir(
        "POST",
        "/tasks",
        json={
            "titulo": titulo,
            "descricao": descricao,
            "estimativa": estimativa,
            "bloco": bloco,
            "prioridade": prioridade,
            "responsavel": responsavel,
            # Marca a autoria para o Falange poder medir a IA depois.
            "origem": "ia",
        },
    )


def listar_tasks(
    bloco: str | None = None,
    status: str | None = None,
    responsavel: str | None = None,
    prioridade: str | None = None,
) -> list | dict:
    """Lista tasks, das mais prioritarias para as menos.

    Filtros opcionais por bloco, status, responsavel e prioridade.
    """
    bloco = _canonizar(bloco, BLOCOS)
    status = _canonizar(status, STATUS)
    prioridade = _canonizar(prioridade, PRIORIDADES)
    for erro in (
        _checar(bloco, BLOCOS, "bloco"),
        _checar(status, STATUS, "status"),
        _checar(prioridade, PRIORIDADES, "prioridade"),
    ):
        if erro:
            return {"erro": erro}

    params = {
        k: v
        for k, v in {
            "bloco": bloco,
            "status": status,
            "responsavel": responsavel,
            "prioridade": prioridade,
        }.items()
        if v
    }
    return _pedir("GET", "/tasks", params=params or None)


def marcar_bloqueio(task_id: int, bloqueada_por: int | None = None) -> dict:
    """Trava a task por outra. bloqueada_por = id da bloqueadora; None desbloqueia."""
    return _pedir(
        "PATCH", f"/tasks/{task_id}/bloqueio", json={"bloqueada_por": bloqueada_por}
    )


def mudar_status(task_id: int, status: str) -> dict:
    """Move a task entre aberta / em_andamento / concluida.

    Concluir limpa o bloqueio da propria task e tambem libera as tasks que
    estavam bloqueadas por ela.
    """
    status = _canonizar(status, STATUS)
    erro = _checar(status, STATUS, "status")
    if erro:
        return {"erro": erro}
    return _pedir("PATCH", f"/tasks/{task_id}/status", json={"status": status})


def editar_task(
    task_id: int,
    titulo: str | None = None,
    descricao: str | None = None,
    estimativa: str | None = None,
    bloco: str | None = None,
    prioridade: str | None = None,
    responsavel: str | None = None,
) -> dict:
    """Corrige campos de uma task existente. So os campos enviados mudam.

    Para remover o responsavel, passe responsavel="" (string vazia).
    """
    estimativa = _canonizar(estimativa, ESTIMATIVAS)
    bloco = _canonizar(bloco, BLOCOS)
    prioridade = _canonizar(prioridade, PRIORIDADES)
    for erro in (
        _checar(estimativa, ESTIMATIVAS, "estimativa"),
        _checar(bloco, BLOCOS, "bloco"),
        _checar(prioridade, PRIORIDADES, "prioridade"),
    ):
        if erro:
            return {"erro": erro}

    campos = {
        k: v
        for k, v in {
            "titulo": titulo,
            "descricao": descricao,
            "estimativa": estimativa,
            "bloco": bloco,
            "prioridade": prioridade,
        }.items()
        if v is not None
    }
    # Convencao: "" remove o responsavel. Filtrar por None nao daria como
    # desatribuir, porque None significa "campo nao enviado".
    if responsavel is not None:
        campos["responsavel"] = responsavel or None
    if not campos:
        return {"erro": "informe ao menos um campo para alterar"}
    return _pedir("PATCH", f"/tasks/{task_id}", json=campos)


def apagar_task(task_id: int) -> dict:
    """Remove a task. Quem dependia dela fica sem bloqueio, nao quebra."""
    return _pedir("DELETE", f"/tasks/{task_id}")


def contar_tasks_por_bloco() -> dict:
    """Quantas tasks existem em cada bloco."""
    return _pedir("GET", "/tasks/contagem-por-bloco")


def verificar_sobrecarga(
    bloco: str | None = None,
    responsavel: str | None = None,
    limite: int | None = None,
) -> dict:
    """Quantas tasks abertas um bloco ou uma pessoa carrega, e se passou do limite.

    Informe bloco OU responsavel. `limite` e opcional: sem ele vale o padrao
    do servidor (LIMITE_SOBRECARGA).
    """
    bloco = _canonizar(bloco, BLOCOS)
    erro = _checar(bloco, BLOCOS, "bloco")
    if erro:
        return {"erro": erro}
    if bloco is None and responsavel is None:
        return {"erro": "informe bloco ou responsavel"}

    params = {
        k: v
        for k, v in {"bloco": bloco, "responsavel": responsavel, "limite": limite}.items()
        if v is not None
    }
    return _pedir("GET", "/carga", params=params)


def sugerir_proximas(
    responsavel: str | None = None,
    bloco: str | None = None,
    limite: int = 5,
) -> dict:
    """Ranking explicado do que da para pegar agora, com alertas da fila.

    E SUGESTAO, nao decisao: apresente os caminhos ao dev com os `motivos` e
    deixe ele escolher. Nao mude status nem prioridade por conta disso.

    Cada sugestao traz `score`, `motivos` (frases prontas) e `destrava`. Os
    `alertas` apontam inversao de prioridade, inflacao de "alta" e trabalho
    parado. Tasks bloqueadas ficam de fora: nao sao escolha do dev.
    """
    erro = _checar(_canonizar(bloco, BLOCOS), BLOCOS, "bloco")
    if erro:
        return {"erro": erro}

    params = {
        k: v
        for k, v in {
            "responsavel": responsavel,
            "bloco": _canonizar(bloco, BLOCOS),
            "limite": limite,
        }.items()
        if v is not None
    }
    return _pedir("GET", "/priorizacao", params=params)


def registrar_decisao(
    tipo: str,
    aceita: bool,
    sugerido: dict | None = None,
    escolhido: dict | None = None,
    motivo: str | None = None,
    responsavel: str | None = None,
    task_id: int | None = None,
) -> dict:
    """Guarda uma escolha feita com opcoes, para o Falange aprender com ela.

    Chame depois de TODA escolha que veio de pergunta, tanto a aceita quanto
    a recusada, com o `motivo` quando o dev disser.

    tipo: proxima_task, prioridade, estimativa, quebrar_task ou pre_task.
    Ponha em `escolhido["rotulo"]` uma etiqueta curta e estavel do caminho
    (ex.: "destravar", "prioritaria", "quebrar"): e por ela que o perfil
    agrupa as decisoes e descobre padrao.
    """
    erro = _checar(tipo, TIPOS_DECISAO, "tipo")
    if erro:
        return {"erro": erro}
    return _pedir(
        "POST",
        "/decisoes",
        json={
            "tipo": tipo,
            "sugerido": sugerido or {},
            "escolhido": escolhido or {},
            "aceita": aceita,
            "motivo": motivo,
            "responsavel": responsavel,
            "task_id": task_id,
        },
    )


def ver_perfil() -> dict:
    """O que o Falange aprendeu com o time ate agora.

    Traz a calibracao, a taxa de aceitacao por tipo de decisao, as correcoes
    humanas mais comuns, as `preferencias_ativas` (que voce deve respeitar) e
    os `padroes_candidatos` (habitos detectados que ninguem confirmou ainda).

    Consulte ANTES de planejar. Nao transforme candidato em regra sozinho.
    """
    return _pedir("GET", "/perfil")


def registrar_preferencia(descricao: str, origem: str = "explicita") -> dict:
    """Guarda uma regra que o time quer que a IA siga.

    `explicita` (alguem pediu) nasce ativa. `inferida` (padrao que voce
    detectou) nasce INATIVA e so vale depois de `confirmar_preferencia`.
    """
    erro = _checar(origem, ORIGENS_PREFERENCIA, "origem")
    if erro:
        return {"erro": erro}
    return _pedir(
        "POST", "/preferencias", json={"descricao": descricao, "origem": origem}
    )


def listar_preferencias(ativa: bool | None = None) -> list | dict:
    """Lista as preferencias. `ativa=True` traz so as que valem agora."""
    params = {"ativa": ativa} if ativa is not None else None
    return _pedir("GET", "/preferencias", params=params)


def confirmar_preferencia(preferencia_id: int) -> dict:
    """Ativa uma preferencia inferida. So com um "sim" explicito do dev."""
    return _pedir("PATCH", f"/preferencias/{preferencia_id}", json={"ativa": True})


def desativar_preferencia(preferencia_id: int) -> dict:
    """Desliga uma preferencia. Pode ser feito a qualquer momento."""
    return _pedir("PATCH", f"/preferencias/{preferencia_id}", json={"ativa": False})


def ver_autonomia() -> dict:
    """Quanto voce pode fazer sozinho, por tipo de acao.

    `nivel`: perguntar (pergunte a cada caso), confirmar_em_lote (faca tudo e
    mostre um resumo para aprovar ou desfazer) ou automatico (faca e reporte
    no fim). Consulte ANTES de cada acao dos quatro tipos.

    `pode` diz se o historico ja permite subir um degrau. Mesmo com true, a
    promocao so acontece com um sim explicito do dev: ofereca no fim da
    tarefa, uma vez, citando o `motivo`.

    Apagar task ou nota nao esta aqui: acao destrutiva nunca fica automatica.
    """
    return _pedir("GET", "/autonomia")


def definir_autonomia(tipo_acao: str, nivel: str) -> dict:
    """Muda o nivel de autonomia de uma acao.

    SUBIR so com pedido ou confirmacao explicita do dev. DESCER voce pode
    sugerir a qualquer momento, e o backend desce sozinho quando o humano
    discorda de algo feito no automatico.
    """
    for erro in (
        _checar(tipo_acao, TIPOS_ACAO, "tipo_acao"),
        _checar(nivel, NIVEIS_AUTONOMIA, "nivel"),
    ):
        if erro:
            return {"erro": erro}
    return _pedir("PATCH", f"/autonomia/{tipo_acao}", json={"nivel": nivel})


def ver_calibracao() -> dict:
    """O que as estimativas do time valeram na pratica, por classe e por bloco.

    Use ANTES de estimar: se PP costuma levar mais que o previsto neste
    projeto, estime com isso em conta em vez de repetir o chute de sempre.
    `veredito` e coerente, superestimada, subestimada ou sem_dados (amostra
    menor que `amostra_minima`). A duracao e tempo corrido, nao esforco.
    """
    return _pedir("GET", "/calibracao")


def ver_configuracao() -> dict:
    """Le o comportamento da plataforma.

    `perguntas_ativas` diz se a IA deve abrir opcoes antes de decidir. Com
    false, decida sozinho e reporte o que escolheu e por que.
    """
    return _pedir("GET", "/configuracao")


def definir_configuracao(perguntas_ativas: bool) -> dict:
    """Liga ou desliga as perguntas de multipla escolha da IA.

    So chame com pedido explicito do dev: e ele quem decide quanto quer ser
    consultado.
    """
    return _pedir(
        "PATCH", "/configuracao", json={"perguntas_ativas": perguntas_ativas}
    )


# --------------------------------------------------------------------------
# notas do time
# --------------------------------------------------------------------------


def registrar_nota(
    texto: str, autor: str | None = None, task_id: int | None = None
) -> dict:
    """Registra uma nota do time: problema, decisao ou duvida que precisa de
    mais gente, sem virar task.

    texto entre 5 e 2000 chars. `task_id` liga a nota a uma task existente.
    """
    return _pedir(
        "POST", "/notas", json={"texto": texto, "autor": autor, "task_id": task_id}
    )


def listar_notas(
    resolvida: bool | None = None, task_id: int | None = None
) -> list | dict:
    """Lista as notas, mais recentes primeiro.

    resolvida=False mostra so as abertas; task_id filtra as de uma task.
    """
    params = {
        k: v
        for k, v in {"resolvida": resolvida, "task_id": task_id}.items()
        if v is not None
    }
    return _pedir("GET", "/notas", params=params or None)


def resolver_nota(nota_id: int) -> dict:
    """Marca a nota como resolvida. Nao apaga: o registro fica no historico."""
    return _pedir("PATCH", f"/notas/{nota_id}/resolver")


def editar_nota(
    nota_id: int,
    texto: str | None = None,
    autor: str | None = None,
    task_id: int | None = None,
    resolvida: bool | None = None,
) -> dict:
    """Corrige uma nota. So os campos enviados mudam.

    `resolvida=False` reabre uma nota fechada por engano; `task_id` liga a
    nota a uma task depois do registro.
    """
    campos = {
        k: v
        for k, v in {
            "texto": texto,
            "autor": autor,
            "task_id": task_id,
            "resolvida": resolvida,
        }.items()
        if v is not None
    }
    if not campos:
        return {"erro": "informe ao menos um campo para alterar"}
    return _pedir("PATCH", f"/notas/{nota_id}", json=campos)


def apagar_nota(nota_id: int) -> dict:
    """Remove a nota de vez. Para so encerrar o assunto, use resolver_nota."""
    return _pedir("DELETE", f"/notas/{nota_id}")


# --------------------------------------------------------------------------
# leitura de arquivo (com raiz permitida)
# --------------------------------------------------------------------------

def _resolver_caminho(caminho: str) -> Path:
    """Resolve dentro de FALANGE_DOCS_ROOT. Recusa qualquer coisa fora.

    Importa porque o servidor SSE pode ser exposto ao time: sem isso a tool
    viraria leitura arbitraria de arquivo na maquina do servidor.
    """
    root = settings.docs_root
    bruto = Path(caminho)
    alvo = (bruto if bruto.is_absolute() else root / bruto).resolve()

    if not alvo.is_relative_to(root):
        raise ValueError(f"caminho fora da raiz permitida ({root}): {caminho}")
    if not alvo.exists():
        raise ValueError(f"arquivo ou pasta nao encontrado: {caminho}")
    # Pasta passa direto: a filtragem por extensao acontece arquivo a arquivo.
    if alvo.is_file() and alvo.suffix.lower() not in EXTENSOES_OK:
        raise ValueError(f"extensao nao suportada: {alvo.suffix}")
    return alvo


def _extrair_estrutura(texto: str) -> dict:
    return {
        "titulos": re.findall(r"^#{1,4}\s+(.+)$", texto, re.M)[:40],
        "marcadores": re.findall(r"(?:TODO|FIXME|XXX|HACK)[:\s]+(.{0,120})", texto)[:20],
        "itens": re.findall(r"^\s*[-*]\s+(.{0,120})$", texto, re.M)[:40],
    }


def _ler_pasta(raiz: Path) -> tuple[str, list[str], list[dict]]:
    """Concatena os arquivos da pasta ate MAX_CHARS_PASTA.

    Devolve (conteudo, lidos, ignorados). Cada ignorado diz o motivo, para a
    IA saber o que ficou de fora em vez de achar que leu tudo.
    """
    candidatos: list[Path] = []
    ignorados: list[dict] = []

    for pasta, subpastas, arquivos in os.walk(raiz):
        atual = Path(pasta)
        podadas = sorted(d for d in subpastas if d in PASTAS_IGNORADAS)
        for nome in podadas:
            ignorados.append(
                {
                    "caminho": f"{(atual / nome).relative_to(raiz).as_posix()}/",
                    "motivo": "pasta ignorada",
                }
            )
        # Poda in-place: os.walk nao desce no que sai desta lista.
        subpastas[:] = sorted(d for d in subpastas if d not in PASTAS_IGNORADAS)

        for nome in sorted(arquivos):
            arquivo = atual / nome
            if arquivo.suffix.lower() in EXTENSOES_OK:
                candidatos.append(arquivo)
            else:
                ignorados.append(
                    {
                        "caminho": arquivo.relative_to(raiz).as_posix(),
                        "motivo": "extensao",
                    }
                )

    # Doc antes de codigo; dentro de cada grupo, ordem alfabetica do caminho.
    candidatos.sort(
        key=lambda a: (
            0 if a.suffix.lower() in EXTENSOES_DOC else 1,
            a.relative_to(raiz).as_posix(),
        )
    )

    partes: list[str] = []
    lidos: list[str] = []
    usado = 0
    estourou = False

    for arquivo in candidatos:
        relativo = arquivo.relative_to(raiz).as_posix()
        if estourou:
            ignorados.append({"caminho": relativo, "motivo": "limite"})
            continue

        corpo = arquivo.read_text(encoding="utf-8", errors="replace")
        bloco = f"=== {relativo} ===\n{corpo}\n"
        if usado + len(bloco) > MAX_CHARS_PASTA:
            # Se nem o primeiro arquivo cabe, entra cortado: melhor material
            # parcial do que devolver nada.
            if not partes:
                partes.append(bloco[:MAX_CHARS_PASTA])
                lidos.append(relativo)
                usado = MAX_CHARS_PASTA
            else:
                ignorados.append({"caminho": relativo, "motivo": "limite"})
            estourou = True
            continue

        partes.append(bloco)
        lidos.append(relativo)
        usado += len(bloco)

    return "".join(partes), lidos, ignorados


def gerar_tasks_a_partir_de_arquivo(caminho: str) -> dict:
    """Le um arquivo OU uma pasta e devolve o material para a IA redigir as
    pre-tasks.

    Pasta e percorrida de forma recursiva, so com as extensoes suportadas,
    pulando dependencia e build; documentacao vem antes de codigo e o
    resultado traz `arquivos_lidos` e `arquivos_ignorados`.

    NAO cria nada no banco e NAO inventa texto: devolve conteudo, estrutura
    extraida, o contrato do template e as tasks que ja existem (para a IA
    nao propor duplicata). Quem redige e a IA que chamou esta tool.
    """
    try:
        alvo = _resolver_caminho(caminho)
    except ValueError as e:
        return {"erro": str(e)}

    if alvo.is_dir():
        texto, lidos, ignorados = _ler_pasta(alvo)
        extra = {"arquivos_lidos": lidos, "arquivos_ignorados": ignorados}
        truncado = any(i["motivo"] == "limite" for i in ignorados)
        tamanho = len(texto)
    else:
        texto = alvo.read_text(encoding="utf-8", errors="replace")
        extra = {}
        truncado = len(texto) > MAX_CHARS
        # tamanho_chars segue sendo o do arquivo inteiro, nao o do trecho.
        tamanho = len(texto)
        texto = texto[:MAX_CHARS]

    # Backend fora do ar nao impede a leitura do arquivo: a IA ainda consegue
    # redigir, so perde a checagem de duplicata.
    atuais = listar_tasks()
    if isinstance(atuais, dict):
        existentes, erro_backend = [], atuais.get("erro")
    else:
        existentes = [
            {"id": t["id"], "titulo": t["titulo"], "bloco": t["bloco"]} for t in atuais
        ]
        erro_backend = None

    return {
        "arquivo": str(alvo),
        "tamanho_chars": tamanho,
        "truncado": truncado,
        "conteudo": texto,
        "estrutura": _extrair_estrutura(texto),
        **extra,
        "template": TEMPLATE_CONTRATO,
        "blocos_validos": list(BLOCOS),
        "estimativas_validas": list(ESTIMATIVAS),
        "tasks_existentes": existentes,
        "aviso_backend": erro_backend,
        "instrucao": (
            "Redija as pre-tasks seguindo exatamente o template acima. "
            "NAO chame criar_task ainda: devolva a lista para revisao humana. "
            "Passe cada uma por validar_task antes de sugerir ao usuario."
        ),
    }


def _classe_da_mediana(calibracao: dict, mediana: float) -> str | None:
    """Em que classe essa duracao real cairia, segundo as faixas do backend."""
    for classe, dados in (calibracao.get("por_estimativa") or {}).items():
        faixa = dados.get("faixa") or {}
        minimo, maximo = faixa.get("minimo_dias"), faixa.get("maximo_dias")
        abaixo_do_teto = maximo is None or mediana <= maximo
        acima_do_piso = minimo is None or mediana >= minimo
        if acima_do_piso and abaixo_do_teto:
            return classe
    return None


def _aviso_calibracao(estimativa: str, bloco: str) -> str | None:
    """Frase curta quando os dados do projeto discordam da estimativa.

    E aviso, nao reprovacao: nao entra em `motivos` e nao muda o veredito.
    O bloco tem precedencia sobre o geral, porque infra e frontend costumam
    ter ritmos diferentes.
    """
    calibracao = ver_calibracao()
    # Backend fora do ar ou resposta inesperada: segue sem aviso, em silencio.
    if not isinstance(calibracao, dict) or calibracao.get("erro"):
        return None

    do_bloco = (calibracao.get("por_bloco") or {}).get(bloco, {}).get(estimativa)
    geral = (calibracao.get("por_estimativa") or {}).get(estimativa)

    for dados, escopo in ((do_bloco, f"em {bloco}"), (geral, "neste projeto")):
        if not dados or dados.get("veredito") not in ("superestimada", "subestimada"):
            continue
        mediana = dados["mediana_dias"]
        sugerida = _classe_da_mediana(calibracao, mediana)
        lado = "mais rapido" if dados["veredito"] == "superestimada" else "mais devagar"
        frase = (
            f"{escopo}, {estimativa} costuma sair {lado} que a faixa "
            f"(mediana {mediana} dias, n={dados['n']})"
        )
        if sugerida and sugerida != estimativa:
            frase += f"; os dados sugerem {sugerida}"
        return frase
    return None


def validar_task(
    titulo: str,
    descricao: str,
    estimativa: str,
    bloco: str,
    prioridade: str = "media",
    checar_duplicata: bool = True,
) -> dict:
    """Veredito sobre uma pre-task: aprovada ou precisa_de_ajuste + motivos."""
    existentes = []
    if checar_duplicata:
        atuais = listar_tasks()
        if not isinstance(atuais, dict):
            existentes = atuais

    veredito = validar_pre_task(
        {
            "titulo": titulo,
            "descricao": descricao,
            "estimativa": estimativa,
            "bloco": bloco,
            "prioridade": prioridade,
        },
        existentes,
    )
    # Campo separado de proposito: a calibracao informa, nao reprova.
    veredito["aviso_calibracao"] = _aviso_calibracao(
        _canonizar(estimativa, ESTIMATIVAS), _canonizar(bloco, BLOCOS)
    )
    return veredito
