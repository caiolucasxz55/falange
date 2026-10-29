"""Leitura do historico do git.

Monta um repositorio de verdade numa pasta temporaria, com commits
escritos para o caso em teste. Nao da para testar isto com mock: o que
precisa de prova e a interacao com o git -- o formato do `--grep`, os
separadores do `--format`, o `--name-only`. Um mock devolveria o que eu
acho que o git devolve, que e exatamente a parte que pode estar errada.
"""

import re
import subprocess

import pytest

from falange_mcp import git


def rodar(raiz, *argumentos):
    resultado = subprocess.run(
        ["git", *argumentos],
        cwd=str(raiz),
        capture_output=True,
        text=True,
        shell=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    return resultado.stdout


@pytest.fixture
def repo(tmp_path):
    """Repositorio com commits citando varias tasks."""
    rodar(tmp_path, "init", "-q", "-b", "main")
    # Identidade local: sem isso o commit falha em maquina sem config
    # global, e o teste quebraria por motivo que nao e o dele.
    rodar(tmp_path, "config", "user.email", "teste@falange.local")
    rodar(tmp_path, "config", "user.name", "Teste")

    def commitar(mensagem, **arquivos):
        for nome, conteudo in arquivos.items():
            (tmp_path / nome).write_text(conteudo, encoding="utf-8")
            rodar(tmp_path, "add", nome)
        rodar(tmp_path, "commit", "-q", "-m", mensagem)

    commitar("feat: comeco, sem citar task", inicio="1")
    commitar("feat: grafo de dependencias (#4)", grafo="a", outro="b")
    commitar("fix: ajuste no grafo (#42)", grafo="aa")
    commitar("feat: criterio de aceite (#420)", criterio="c")
    commitar("chore: mexe em 4 arquivos, sem id no titulo", quatro="4")
    return tmp_path


def test_reconhece_repositorio(repo):
    assert git.e_repositorio(repo) is True


def test_pasta_fora_de_repositorio_nao_passa(tmp_path):
    """A pasta tem de estar FORA do repo do teste.

    `git rev-parse` sobe na arvore de diretorios, entao uma subpasta de
    `tmp_path` (que e o repo) responderia que sim.
    """
    solta = tmp_path.parent / f"{tmp_path.name}-solta"
    solta.mkdir()
    assert git.e_repositorio(solta) is False


def test_padrao_nao_casa_id_mais_longo():
    padrao = git.padrao_do_id(42)
    assert re.search(padrao, "fix: ajuste (#42)")
    assert re.search(padrao, "fix: ajuste #42")
    assert not re.search(padrao, "feat: coisa (#420)")
    assert not re.search(padrao, "feat: coisa (#421)")


def test_acha_so_os_commits_da_task_pedida(repo):
    commits, erro = git.commits_da_task(42, repo)
    assert erro is None
    assert [c["titulo"] for c in commits] == ["fix: ajuste no grafo (#42)"]


def test_id_curto_nao_arrasta_os_longos(repo):
    """A task 4 nao deve trazer os commits da 42 e da 420.

    Sem o grupo final no regex, buscar a 4 traria tudo de 40 a 49 -- e a
    evidencia da 4 ficaria cheia de trabalho que nao e dela.
    """
    commits, erro = git.commits_da_task(4, repo)
    assert erro is None
    assert [c["titulo"] for c in commits] == ["feat: grafo de dependencias (#4)"]


def test_traz_sha_data_autor_e_arquivos(repo):
    commits, erro = git.commits_da_task(4, repo)
    assert erro is None
    (commit,) = commits
    assert re.fullmatch(r"[0-9a-f]{40}", commit["sha"])
    assert commit["sha_curto"] == commit["sha"][:7]
    assert commit["autor"] == "Teste"
    # ISO 8601 com timezone, como o resto da API.
    assert re.match(r"\d{4}-\d{2}-\d{2}T", commit["data"])
    assert sorted(commit["arquivos"]) == ["grafo", "outro"]


def test_task_sem_commit_devolve_lista_vazia_nao_erro(repo):
    commits, erro = git.commits_da_task(999, repo)
    assert erro is None
    assert commits == []


def test_diff_recusa_sha_que_nao_e_sha(repo):
    diff, erro = git.diff_do_commit("sei la", repo)
    assert diff is None
    assert "nao e um sha" in erro


def test_diff_mostra_o_que_mudou(repo):
    commits, _ = git.commits_da_task(42, repo)
    diff, erro = git.diff_do_commit(commits[0]["sha"], repo)
    assert erro is None
    assert "grafo" in diff
    # O conteudo novo aparece no diff: e isso que permite conferir em vez
    # de acreditar no titulo do commit.
    assert "+aa" in diff


def test_diff_limitado_a_um_arquivo(repo):
    """O commit tocou dois arquivos; o diff pedido mostra um.

    A assercao olha os cabecalhos `diff --git`, nao o texto todo: o titulo
    do commit vem no formato e por acaso contem a palavra "grafo", que e o
    nome do outro arquivo.
    """
    commits, _ = git.commits_da_task(4, repo)
    assert sorted(commits[0]["arquivos"]) == ["grafo", "outro"]

    diff, erro = git.diff_do_commit(commits[0]["sha"], repo, arquivo="outro")
    assert erro is None

    cabecalhos = [l for l in diff.splitlines() if l.startswith("diff --git")]
    assert len(cabecalhos) == 1
    assert "outro" in cabecalhos[0]


def test_sha_invalido_nao_chega_a_linha_de_comando(repo):
    """Nada vindo da conversa pode virar argumento de shell.

    O modulo roda `subprocess` com LISTA e `shell=False`, mas o sha ainda
    passa por um fullmatch antes: defesa em profundidade, porque esta e a
    unica funcao do projeto que executa um binario externo.
    """
    for veneno in ["; rm -rf /", "HEAD", "--upload-pack=x", "$(whoami)", ""]:
        diff, erro = git.diff_do_commit(veneno, repo)
        assert diff is None, veneno
        assert erro
