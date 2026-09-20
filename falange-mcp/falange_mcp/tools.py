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
from falange_mcp.template import BLOCOS, ESTIMATIVAS, TEMPLATE_CONTRATO, validar_pre_task

BACKEND = settings.backend_url

EXTENSOES_OK = {
    ".md", ".txt", ".rst", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".json", ".yaml", ".yml", ".toml", ".sql", ".sh",
}
MAX_CHARS = 20_000


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
    r = httpx.post(
        f"{BACKEND}/tasks",
        json={
            "titulo": titulo,
            "descricao": descricao,
            "estimativa": estimativa,
            "bloco": bloco,
            "responsavel": responsavel,
        },
    )
    r.raise_for_status()
    return r.json()


def listar_tasks(
    bloco: str | None = None,
    status: str | None = None,
    responsavel: str | None = None,
) -> list:
    params = {
        k: v
        for k, v in {"bloco": bloco, "status": status, "responsavel": responsavel}.items()
        if v
    }
    r = httpx.get(f"{BACKEND}/tasks", params=params or None)
    r.raise_for_status()
    return r.json()


def marcar_bloqueio(task_id: int, bloqueada_por: int | None = None) -> dict:
    """bloqueada_por = id da task que trava esta. None desbloqueia."""
    r = httpx.patch(
        f"{BACKEND}/tasks/{task_id}/bloqueio", json={"bloqueada_por": bloqueada_por}
    )
    if r.status_code == 409:
        return {"erro": r.json().get("detail")}
    r.raise_for_status()
    return r.json()


def contar_tasks_por_bloco() -> dict:
    r = httpx.get(f"{BACKEND}/tasks/contagem-por-bloco")
    r.raise_for_status()
    return r.json()


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
    r = httpx.get(f"{BACKEND}/carga", params=params)
    if r.status_code == 400:
        return {"erro": r.json().get("detail")}
    r.raise_for_status()
    return r.json()


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

    try:
        existentes = [
            {"id": t["id"], "titulo": t["titulo"], "bloco": t["bloco"]}
            for t in listar_tasks()
        ]
    except Exception as e:  # backend fora do ar nao impede a leitura
        existentes = []
        erro_backend = str(e)
    else:
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
        try:
            existentes = listar_tasks()
        except Exception:
            existentes = []

    return validar_pre_task(
        {
            "titulo": titulo,
            "descricao": descricao,
            "estimativa": estimativa,
            "bloco": bloco,
        },
        existentes,
    )
