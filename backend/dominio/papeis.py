"""Quem pode fazer o que. Modulo puro: entra papel e acao, sai bool.

Uma tabela so, explicita, em vez de `if papel == "admin"` espalhado pelas
rotas. Permissao que mora em varios lugares divergem; esta nao tem onde se
esconder, e o teste percorre a matriz inteira.

Os quatro papeis humanos sao uma escada: admin manda em tudo, lead decide o
que o time faz, dev executa, leitor so olha. `ia` nao entra nessa escada:
ela faz o trabalho de um dev e NAO aumenta a confianca em si mesma -- nem
promove autonomia, nem ativa preferencia, nem mexe em usuario. Essa trava
era do cliente (o `ask` do .claude/settings.json) e agora e da API.
"""

from typing import Optional

# Papeis humanos, do mais para o menos poderoso.
PAPEIS_HUMANOS = ("admin", "lead", "dev", "leitor")

# `ia` fica de fora da escada: e uma conta de servico, nao uma pessoa.
PAPEL_IA = "ia"

PAPEIS = PAPEIS_HUMANOS + (PAPEL_IA,)

# Toda acao que a API protege. Acao que nao esta aqui nao e protegida: a
# lista e a fonte de verdade, e o teste cobra que cada uma apareca na matriz.
ACOES = (
    "ler",
    "criar_task",
    "editar_task",
    "definir_prioridade",
    "atribuir_responsavel",
    "mudar_status_task",
    "marcar_bloqueio",
    "apagar_task",
    "apagar_task_propria",
    "criar_nota",
    "editar_nota",
    "resolver_nota",
    "apagar_nota",
    "apagar_nota_propria",
    "registrar_decisao",
    "criar_preferencia",
    "ativar_preferencia",
    "promover_autonomia",
    "rebaixar_autonomia",
    "definir_configuracao",
    "gerir_usuarios",
)

# A matriz. Ler na vertical: o que cada papel alcanca.
#
# `apagar_*_propria` existe para o dev: ele apaga o que criou, nao o que o
# time criou. A rota tenta a acao ampla primeiro e cai na restrita, ai
# comparando o autor.
_MATRIZ: dict[str, tuple[str, ...]] = {
    "admin": ACOES,
    "lead": (
        "ler",
        "criar_task",
        "editar_task",
        "definir_prioridade",
        "atribuir_responsavel",
        "mudar_status_task",
        "marcar_bloqueio",
        "apagar_task",
        "apagar_task_propria",
        "criar_nota",
        "editar_nota",
        "resolver_nota",
        "apagar_nota",
        "apagar_nota_propria",
        "registrar_decisao",
        "criar_preferencia",
        "ativar_preferencia",
        "promover_autonomia",
        "rebaixar_autonomia",
    ),
    "dev": (
        "ler",
        "criar_task",
        "editar_task",
        "mudar_status_task",
        "marcar_bloqueio",
        "apagar_task_propria",
        "criar_nota",
        "editar_nota",
        "resolver_nota",
        "apagar_nota_propria",
        "registrar_decisao",
        "criar_preferencia",
        "rebaixar_autonomia",
    ),
    "leitor": ("ler",),
    # A IA trabalha como um dev, e apaga como um dev (so o que ela criou).
    # O que ela NAO tem: ativar_preferencia, promover_autonomia,
    # definir_configuracao e gerir_usuarios. Rebaixar ela pode, sempre:
    # perder confianca e seguro em qualquer direcao.
    PAPEL_IA: (
        "ler",
        "criar_task",
        "editar_task",
        "definir_prioridade",
        "mudar_status_task",
        "marcar_bloqueio",
        "apagar_task_propria",
        "criar_nota",
        "editar_nota",
        "resolver_nota",
        "apagar_nota_propria",
        "registrar_decisao",
        "criar_preferencia",
        "rebaixar_autonomia",
    ),
}

PERMISSOES: dict[str, frozenset[str]] = {
    papel: frozenset(acoes) for papel, acoes in _MATRIZ.items()
}


def papel_valido(papel: Optional[str]) -> bool:
    return papel in PERMISSOES


def pode(papel: Optional[str], acao: str) -> bool:
    """O papel alcanca a acao?

    Papel desconhecido ou ausente nao alcanca nada: na duvida, barra. Acao
    desconhecida tambem e False, para um erro de digitacao no nome da acao
    nao abrir a porta sem ninguem notar.
    """
    if acao not in ACOES:
        return False
    return acao in PERMISSOES.get(papel or "", frozenset())


def acoes_de(papel: Optional[str]) -> list[str]:
    """O que este papel alcanca, na ordem de ACOES. Alimenta a tela."""
    permitidas = PERMISSOES.get(papel or "", frozenset())
    return [acao for acao in ACOES if acao in permitidas]


# Prioridade que uma task assume quando ninguem escolhe. Escrever ESTE valor
# nao e "definir prioridade": e aceitar o padrao.
PRIORIDADE_PADRAO = "media"


def acoes_para_campos(campos: dict, nome_chamador: Optional[str]) -> set[str]:
    """Permissoes extras que os campos desta escrita exigem.

    Criar e editar task passam por aqui. A ideia: descrever o trabalho e de
    quem executa, decidir a fila e de quem lidera.

    Duas folgas deliberadas, para a regra nao virar burocracia:

    - gravar a prioridade PADRAO nao exige nada -- senao um dev nao
      conseguiria abrir uma task;
    - se atribuir a SI MESMO nao exige nada -- pegar trabalho e diferente de
      distribuir trabalho para os outros.
    """
    extras: set[str] = set()

    if "prioridade" in campos:
        valor = getattr(campos["prioridade"], "value", campos["prioridade"])
        if valor is not None and valor != PRIORIDADE_PADRAO:
            extras.add("definir_prioridade")

    if "responsavel" in campos:
        alvo = campos["responsavel"]
        # Limpar o campo e abrir mao, nao distribuir.
        proprio = alvo in (None, "") or (
            nome_chamador is not None
            and alvo.strip().lower() == nome_chamador.strip().lower()
        )
        if not proprio:
            extras.add("atribuir_responsavel")

    return extras
