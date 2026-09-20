"""Logica das tools do Falange.

Este modulo NAO sabe o que e stdio ou SSE. Nenhum import de transporte,
nenhum decorator de servidor. Sao funcoes Python comuns -- o que permite
testar cada uma sem subir servidor nenhum.

Regra: as tools falam com o backend por HTTP. Nunca com o Postgres direto.
"""

import re
from pathlib import Path

import httpx

from config import settings
from falange_mcp.template import (
    BLOCOS,
    ESTIMATIVAS,
    STATUS,
    TEMPLATE_CONTRATO,
    validar_pre_task,
)

BACKEND = settings.backend_url

EXTENSOES_OK = {
    ".md", ".txt", ".rst", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".json", ".yaml", ".yml", ".toml", ".sql", ".sh",
}
MAX_CHARS = 20_000


def _erro_422(corpo: dict) -> str:
    """Traduz o 422 do FastAPI em uma frase acionavel."""
    partes = []
    for item in corpo.get("detail", []):
        campo = ".".join(str(x) for x in item.get("loc", []) if x != "body")
        partes.append(f"{campo}: {item.get('msg', 'invalido')}")
    return "; ".join(partes) or "payload invalido"


def _pedir(metodo: str, caminho: str, **kw):
    """Chama o backend e NUNCA levanta: devolve o json ou {'erro': <frase>}.

    Uma excecao vira 'Error executing tool X' do lado do client MCP, o que
    nao diz nada para a IA. Um dict com 'erro' ela consegue ler e corrigir.
    """
    try:
        r = httpx.request(metodo, f"{BACKEND}{caminho}", timeout=10, **kw)
    except httpx.HTTPError as e:
        return {"erro": f"backend inacessivel em {BACKEND}: {e}"}

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


def _checar(valor, validos, campo: str) -> str | None:
    if valor is not None and valor not in validos:
        return f"{campo} '{valor}' invalido; use {'/'.join(validos)}"
    return None


# --------------------------------------------------------------------------
# tools que so repassam para o backend
# --------------------------------------------------------------------------

def criar_task(
    titulo: str,
    estimativa: str,
    bloco: str,
    descricao: str = "",
    responsavel: str | None = None,
) -> dict:
    """Cria uma task. estimativa: PP/P/M/G. bloco: frontend/backend/infra/seguranca."""
    for erro in (
        _checar(estimativa, ESTIMATIVAS, "estimativa"),
        _checar(bloco, BLOCOS, "bloco"),
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
            "responsavel": responsavel,
        },
    )


def listar_tasks(
    bloco: str | None = None,
    status: str | None = None,
    responsavel: str | None = None,
) -> list | dict:
    """Lista tasks. Filtros opcionais por bloco, status e responsavel."""
    for erro in (_checar(bloco, BLOCOS, "bloco"), _checar(status, STATUS, "status")):
        if erro:
            return {"erro": erro}

    params = {
        k: v
        for k, v in {"bloco": bloco, "status": status, "responsavel": responsavel}.items()
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

    Concluir limpa o bloqueio automaticamente.
    """
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
    responsavel: str | None = None,
) -> dict:
    """Corrige campos de uma task existente. So os campos enviados mudam."""
    for erro in (
        _checar(estimativa, ESTIMATIVAS, "estimativa"),
        _checar(bloco, BLOCOS, "bloco"),
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
            "responsavel": responsavel,
        }.items()
        if v is not None
    }
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
    params = {
        k: v
        for k, v in {"bloco": bloco, "responsavel": responsavel, "limite": limite}.items()
        if v is not None
    }
    return _pedir("GET", "/carga", params=params)


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
    if not alvo.exists() or not alvo.is_file():
        raise ValueError(f"arquivo nao encontrado: {caminho}")
    if alvo.suffix.lower() not in EXTENSOES_OK:
        raise ValueError(f"extensao nao suportada: {alvo.suffix}")
    return alvo


def _extrair_estrutura(texto: str) -> dict:
    return {
        "titulos": re.findall(r"^#{1,4}\s+(.+)$", texto, re.M)[:40],
        "marcadores": re.findall(r"(?:TODO|FIXME|XXX|HACK)[:\s]+(.{0,120})", texto)[:20],
        "itens": re.findall(r"^\s*[-*]\s+(.{0,120})$", texto, re.M)[:40],
    }


def gerar_tasks_a_partir_de_arquivo(caminho: str) -> dict:
    """Le um arquivo e devolve o material para a IA redigir as pre-tasks.

    NAO cria nada no banco e NAO inventa texto: devolve conteudo, estrutura
    extraida, o contrato do template e as tasks que ja existem (para a IA
    nao propor duplicata). Quem redige e a IA que chamou esta tool.
    """
    try:
        alvo = _resolver_caminho(caminho)
    except ValueError as e:
        return {"erro": str(e)}

    texto = alvo.read_text(encoding="utf-8", errors="replace")
    truncado = len(texto) > MAX_CHARS

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
        "tamanho_chars": len(texto),
        "truncado": truncado,
        "conteudo": texto[:MAX_CHARS],
        "estrutura": _extrair_estrutura(texto),
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


def validar_task(
    titulo: str, descricao: str, estimativa: str, bloco: str, checar_duplicata: bool = True
) -> dict:
    """Veredito sobre uma pre-task: aprovada ou precisa_de_ajuste + motivos."""
    existentes = []
    if checar_duplicata:
        atuais = listar_tasks()
        if not isinstance(atuais, dict):
            existentes = atuais

    return validar_pre_task(
        {
            "titulo": titulo,
            "descricao": descricao,
            "estimativa": estimativa,
            "bloco": bloco,
        },
        existentes,
    )
