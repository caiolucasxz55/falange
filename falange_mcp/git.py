"""Leitura do historico do git, para transformar commit em evidencia.

So LE. Nenhuma funcao daqui escreve no repositorio -- nem `add`, nem
`commit`, nem `checkout`. Commitar continua sendo do dev.

`subprocess` com LISTA de argumentos e `shell=False`: o id da task entra
num regex montado a partir de um int, e nada do que vem da conversa chega
a uma linha de comando interpretada por shell.
"""

import re
import subprocess
from pathlib import Path
from typing import Optional

# Separadores improvaveis num titulo de commit. \x1e separa commits, \x1f
# separa campos -- sao os caracteres ASCII para exatamente isso.
_REG = "\x1e"
_CAMPO = "\x1f"

# Teto de commits lidos. Uma task com mais de 50 commits citando ela nao vai
# ser esclarecida pelo 51o, e a saida tem de caber na conversa.
MAX_COMMITS = 50

# Segundos. Repositorio grande com historico longo pode demorar; travar a
# sessao do dev para sempre, nao.
TIMEOUT = 20


def _rodar(
    argumentos: list[str], raiz: Path
) -> tuple[Optional[str], Optional[str]]:
    """`(saida, None)` ou `(None, erro)`. Nunca levanta."""
    try:
        resultado = subprocess.run(
            ["git", *argumentos],
            cwd=str(raiz),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
            shell=False,
        )
    except FileNotFoundError:
        return None, "git nao encontrado no PATH desta maquina"
    except subprocess.TimeoutExpired:
        return None, f"git passou de {TIMEOUT}s e foi interrompido"
    except OSError as erro:
        return None, f"nao deu para rodar git: {erro}"

    if resultado.returncode != 0:
        detalhe = (resultado.stderr or "").strip().splitlines()
        return None, detalhe[0] if detalhe else f"git saiu com {resultado.returncode}"
    return resultado.stdout, None


def e_repositorio(raiz: Path) -> bool:
    saida, _ = _rodar(["rev-parse", "--git-dir"], raiz)
    return saida is not None


def padrao_do_id(task_id: int) -> str:
    """Regex que casa `#42` mas nao `#420`.

    Sem o grupo final, buscar a task 4 traria todo commit das tasks 40 a
    49 -- e a evidencia da 4 ficaria cheia de trabalho que nao e dela.
    """
    return rf"#{int(task_id)}([^0-9]|$)"


def commits_da_task(
    task_id: int, raiz: Path, limite: int = MAX_COMMITS
) -> tuple[Optional[list[dict]], Optional[str]]:
    """Commits cujo titulo ou corpo cita `#<task_id>`.

    Cada um sai com sha, sha curto, titulo, data ISO, autor e arquivos
    tocados -- o bastante para alguem conferir com `git show` depois.
    """
    if not e_repositorio(raiz):
        return None, f"'{raiz}' nao e um repositorio git"

    formato = _REG + _CAMPO.join(["%H", "%s", "%cI", "%an"])
    saida, erro = _rodar(
        [
            "log",
            "--extended-regexp",
            f"--grep={padrao_do_id(task_id)}",
            f"--max-count={int(limite)}",
            "--name-only",
            f"--format={formato}",
        ],
        raiz,
    )
    if erro:
        return None, erro

    commits = []
    for bruto in (saida or "").split(_REG):
        if not bruto.strip():
            continue
        cabecalho, _, resto = bruto.partition("\n")
        partes = cabecalho.split(_CAMPO)
        if len(partes) != 4:
            continue
        sha, titulo, data, autor = partes
        commits.append(
            {
                "sha": sha,
                # O sha curto e o que se digita; o completo e o que se
                # registra como referencia.
                "sha_curto": sha[:7],
                "titulo": titulo,
                "data": data,
                "autor": autor,
                "arquivos": [l for l in resto.splitlines() if l.strip()],
            }
        )
    return commits, None


def diff_do_commit(
    sha: str, raiz: Path, arquivo: Optional[str] = None
) -> tuple[Optional[str], Optional[str]]:
    """O diff de um commit, opcionalmente de um arquivo so.

    Serve ao `/falange-verificar`: ler o que mudou e o que permite dizer se
    um criterio foi cumprido, em vez de acreditar no titulo do commit.
    """
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", sha or ""):
        return None, f"'{sha}' nao e um sha de commit"

    argumentos = ["show", "--format=%H%n%s%n%cI%n", sha.lower()]
    if arquivo:
        # `--` separa revisao de caminho: sem isso, um arquivo com nome de
        # branch seria lido como revisao.
        argumentos += ["--", arquivo]
    return _rodar(argumentos, raiz)
