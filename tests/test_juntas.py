"""As juntas: listas que vivem em arquivos diferentes e tem de concordar.

O code review da V2 achou nove defeitos, e SETE eram de junta -- painel
contra compose, portao de evidencia contra token de conexao, validacao de
marco contra a validacao equivalente das dependencias. Nenhum teste pegou,
e nao foi por falta de cobertura: cada lado estava certo sozinho, e os
testes existentes olham um lado de cada vez.

Este arquivo olha os DOIS lados. Toda lista aqui e uma duplicata que o
projeto assume de proposito -- o MCP nao importa de `backend/`, o
TypeScript nao importa de Python -- e duplicata assumida precisa de quem
cobre o alinhamento, senao ela diverge no dia em que alguem acrescenta um
valor so de um lado.

Quando um destes testes falhar, a correcao quase nunca e mexer no teste: e
acrescentar o valor que faltou no outro arquivo.
"""

import json
import pathlib
import re

import pytest

from backend.dominio import autonomia as dom_autonomia
from backend.dominio import papeis
from backend.models import enums
from backend.models.evidencia import TipoEvidencia
from falange_mcp import server, template

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def texto(caminho: pathlib.Path) -> str:
    assert caminho.exists(), f"sumiu do repositorio: {caminho}"
    return caminho.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# o MCP espelha os enums do backend
# ---------------------------------------------------------------------------

# `falange_mcp/` nao importa nada de `backend/` -- e regra do projeto, para
# o MCP nao conhecer o banco nem por engano. O preco e repetir os enums, e
# este teste e o que paga o preco.
ESPELHOS = [
    ("ESTIMATIVAS", template.ESTIMATIVAS, enums.Estimativa),
    ("BLOCOS", template.BLOCOS, enums.Bloco),
    ("STATUS", template.STATUS, enums.Status),
    ("PRIORIDADES", template.PRIORIDADES, enums.Prioridade),
    ("ORIGENS_PREFERENCIA", template.ORIGENS_PREFERENCIA, enums.OrigemPreferencia),
    ("TIPOS_ACAO", template.TIPOS_ACAO, enums.TipoAcao),
    ("NIVEIS_AUTONOMIA", template.NIVEIS_AUTONOMIA, enums.NivelAutonomia),
    ("TIPOS_EVIDENCIA", template.TIPOS_EVIDENCIA, TipoEvidencia),
]


@pytest.mark.parametrize("nome,do_mcp,do_backend", ESPELHOS, ids=lambda x: x if isinstance(x, str) else "")
def test_o_mcp_espelha_o_enum_do_backend(nome, do_mcp, do_backend):
    valores = {v.value for v in do_backend}
    assert set(do_mcp) == valores, (
        f"{nome} no MCP nao bate com {do_backend.__name__} no backend. "
        f"So no MCP: {set(do_mcp) - valores or '-'}. "
        f"So no backend: {valores - set(do_mcp) or '-'}. "
        "O MCP nao importa de backend/ de proposito, entao o alinhamento e "
        "manual -- acrescente o valor no outro lado."
    )


def test_tipos_de_decisao_omitem_so_o_que_a_ia_nao_registra():
    """`TIPOS_DECISAO` e subconjunto, e a omissao e deliberada.

    `ajuste_humano` nao e um tipo que a IA pode registrar: ele e escrito
    pelo BACKEND quando um humano corrige um campo que ela escolheu.
    Deixar a IA mandar esse tipo seria deixa-la registrar que foi
    corrigida -- ou que nao foi.

    A lista de excecoes e fechada: um tipo novo que a IA deva registrar
    faz este teste falhar ate ser acrescentado ao MCP.
    """
    so_do_backend = {"ajuste_humano"}
    valores = {v.value for v in enums.TipoDecisao}

    assert set(template.TIPOS_DECISAO) <= valores, (
        f"o MCP conhece tipo que o backend nao tem: "
        f"{set(template.TIPOS_DECISAO) - valores}"
    )
    assert valores - set(template.TIPOS_DECISAO) == so_do_backend, (
        f"mudou o conjunto de tipos que a IA nao registra. Esperado "
        f"{so_do_backend}, achei {valores - set(template.TIPOS_DECISAO)}"
    )


# ---------------------------------------------------------------------------
# toda tool tem permissao registrada
# ---------------------------------------------------------------------------

SERVIDORES = ("falange", "falange-teste")


def permissoes() -> dict[str, set[str]]:
    dados = json.loads(texto(RAIZ / ".claude" / "settings.json"))
    return {
        chave: set(dados["permissions"].get(chave, []))
        for chave in ("allow", "ask")
    }


def test_toda_tool_do_mcp_tem_permissao_nos_dois_servidores():
    """Tool sem entrada no settings vira prompt a cada chamada.

    O `CLAUDE.md` manda registrar, e registrar em DOIS lugares (o backlog
    real e o sandbox) -- o que e exatamente o tipo de passo que se esquece
    pela metade.
    """
    registradas = permissoes()
    conhecidas = registradas["allow"] | registradas["ask"]

    faltando = [
        f"mcp__{servidor}__{fn.__name__}"
        for fn in server.TOOLS
        for servidor in SERVIDORES
        if f"mcp__{servidor}__{fn.__name__}" not in conhecidas
    ]
    assert not faltando, (
        "tools sem permissao em .claude/settings.json: "
        f"{faltando}. `allow` para leitura e escrita comum, `ask` se for "
        "destrutiva."
    )


def test_nao_ha_permissao_para_tool_que_nao_existe_mais():
    """Entrada orfa aponta para uma tool renomeada ou removida.

    Nao e perigoso, e e sinal de que uma renomeacao passou pela metade --
    foi o que aconteceu com `marcar_bloqueio` quando ele virou
    `adicionar_dependencia`.
    """
    registradas = permissoes()
    existentes = {fn.__name__ for fn in server.TOOLS}

    orfas = set()
    for entrada in registradas["allow"] | registradas["ask"]:
        achado = re.fullmatch(r"mcp__(falange|falange-teste)__(\w+)", entrada)
        if achado and achado.group(2) not in existentes:
            orfas.add(entrada)
    assert not orfas, f"permissao para tool inexistente: {sorted(orfas)}"


def test_o_que_apaga_esta_em_ask_e_nao_em_allow():
    """Acao destrutiva pergunta. E regra do projeto, e da para conferir."""
    registradas = permissoes()
    destrutivas = [
        f"mcp__{servidor}__{fn.__name__}"
        for fn in server.TOOLS
        for servidor in SERVIDORES
        if fn.__name__.startswith("apagar")
    ]
    no_allow = [d for d in destrutivas if d in registradas["allow"]]
    assert not no_allow, f"tool que apaga liberada sem perguntar: {no_allow}"
    assert destrutivas, "a varredura nao achou tool destrutiva nenhuma"


# ---------------------------------------------------------------------------
# a tela conhece as acoes do backend
# ---------------------------------------------------------------------------


def acoes_do_frontend() -> set[str]:
    """Os membros do union `Acao` em `frontend/types/task.ts`."""
    fonte = texto(RAIZ / "frontend" / "types" / "task.ts")
    bloco = re.search(r"export type Acao =(.*?);", fonte, re.S)
    assert bloco, "nao achei o union `Acao` em types/task.ts"
    return set(re.findall(r'"(\w+)"', bloco.group(1)))


def test_o_union_acao_da_tela_cobre_todas_as_acoes_do_backend():
    """`pode("x")` so compila com `x` no union.

    Uma acao nova no backend sem entrada aqui NAO quebra o build -- ela
    simplesmente nunca e consultada, e a tela deixa de esconder o botao
    que vai dar 403. O sintoma aparece para o usuario, nao para quem
    escreveu.
    """
    do_backend = set(papeis.ACOES)
    da_tela = acoes_do_frontend()

    assert da_tela == do_backend, (
        f"So no backend: {sorted(do_backend - da_tela) or '-'}. "
        f"So na tela: {sorted(da_tela - do_backend) or '-'}."
    )


def test_o_painel_de_autonomia_rotula_toda_acao_com_autonomia():
    """Sem rotulo, o painel mostra a chave crua (`concluir_com_evidencia`).

    Aconteceu: a fase F acrescentou o valor ao enum e o painel ficou para
    tras, exibindo o identificador em vez do texto.
    """
    fonte = texto(RAIZ / "frontend" / "components" / "PainelAutonomia.tsx")
    bloco = re.search(r"const ROTULO_ACAO[^{]*\{(.*?)\n\};", fonte, re.S)
    assert bloco, "nao achei ROTULO_ACAO em PainelAutonomia.tsx"
    rotulados = set(re.findall(r"^\s*(\w+):", bloco.group(1), re.M))

    faltando = set(dom_autonomia.ACOES) - rotulados
    assert not faltando, (
        f"acoes sem rotulo no painel de autonomia: {sorted(faltando)} -- "
        "elas aparecem na tela como o identificador cru"
    )
