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

from typing import Any, Optional

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
    # A IA apaga como um dev (so o que ela criou), mas decide prioridade e
    # responsavel como um lead -- de proposito: ali ela esta TRANSCREVENDO o
    # pedido do dev ("cria uma task pra Caio, alta"), nao dirigindo ninguem.
    #
    # A isencao de "atribuir a si mesmo" nao serve para ela: o `nome` dela e
    # "Falange IA", entao sem a permissao ampla o parametro `responsavel` da
    # tool falhava em TODO caso -- e a tool continuava anunciando o campo.
    #
    # O que ela NAO tem: ativar_preferencia, promover_autonomia,
    # definir_configuracao e gerir_usuarios. Essas quatro aumentam a
    # confianca nela ou mexem em quem e quem; nenhuma e transcricao.
    # Rebaixar ela pode, sempre: perder confianca e seguro em toda direcao.
    PAPEL_IA: (
        "ler",
        "criar_task",
        "editar_task",
        "definir_prioridade",
        "atribuir_responsavel",
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


def admin_sem_login(exigir_login: bool, existe_conta_humana: bool) -> bool:
    """O token compartilhado, sozinho, ainda vale como admin?

    Existe UMA razao para isso valer: criar o primeiro admin. Sem essa
    brecha, um banco novo nao teria como ganhar o primeiro usuario pela API.

    Ela fecha na primeira conta humana criada, e isso nao e zelo: enquanto
    ficava aberta, qualquer pessoa escalava privilegio apagando o proprio
    cookie de sessao no devtools -- a tela cai no token compartilhado, e o
    token compartilhado era admin. `HttpOnly` nao protege disso: ele impede
    o JavaScript de LER o cookie, nao a pessoa de apaga-lo.

    `exigir_login` fecha a brecha de uma vez, inclusive no banco vazio -- ai
    o primeiro admin tem de ser criado por fora da API.
    """
    if exigir_login:
        return False
    return not existe_conta_humana


# Prioridade que uma task assume quando ninguem escolhe. Escrever ESTE valor
# nao e "definir prioridade": e aceitar o padrao.
PRIORIDADE_PADRAO = "media"


def _texto(valor: Any) -> Any:
    """Enum do SQLAlchemy vira o texto; o resto passa igual."""
    return getattr(valor, "value", valor)


def _mesmo_nome(a: Optional[str], b: Optional[str]) -> bool:
    """Compara nome ignorando caixa e espaco nas pontas."""
    if a is None or b is None:
        return a == b
    return a.strip().lower() == b.strip().lower()


def acoes_para_campos(
    campos: dict,
    nome_chamador: Optional[str],
    atuais: Optional[dict] = None,
) -> set[str]:
    """Permissoes extras que os campos desta escrita exigem.

    Criar e editar task passam por aqui. A ideia: descrever o trabalho e de
    quem executa, decidir a fila e de quem lidera.

    `atuais` sao os valores que a task tem hoje; None significa criacao.
    Passar isso importa porque a pergunta certa e "o que esta MUDANDO", nao
    "que campos vieram no corpo". Olhando so a presenca, o formulario de
    edicao -- que reenvia a task inteira -- fazia um dev levar 403 ao
    corrigir um typo no titulo de qualquer task `alta`. E, ao mesmo tempo,
    deixava esse dev rebaixar `alta` para `media` de graca, porque o valor
    padrao era isento.

    Duas folgas deliberadas, para a regra nao virar burocracia:

    - na CRIACAO, gravar a prioridade padrao nao exige nada -- senao um dev
      nao conseguiria abrir uma task. Na edicao nao existe isencao por
      valor: mudar para `media` e mudar a prioridade como qualquer outra.
    - atribuir a SI MESMO nao exige nada, nem na criacao nem na edicao --
      pegar trabalho e diferente de distribuir trabalho para os outros. E,
      pela mesma logica, LARGAR a task so e livre se ela for sua: tirar
      outra pessoa de uma task e distribuir trabalho, nao abrir mao.
    """
    extras: set[str] = set()
    criando = atuais is None

    if "prioridade" in campos:
        novo = _texto(campos["prioridade"])
        if criando:
            # Sem valor anterior para comparar: so o padrao e isento.
            if novo is not None and novo != PRIORIDADE_PADRAO:
                extras.add("definir_prioridade")
        elif novo != _texto(atuais.get("prioridade")):
            extras.add("definir_prioridade")

    if "responsavel" in campos:
        alvo = campos["responsavel"]
        atual = None if criando else atuais.get("responsavel")
        if not _mesmo_nome(alvo, atual):
            vazio = alvo in (None, "")
            pegando_para_si = _mesmo_nome(alvo, nome_chamador)
            # Largar: livre so quando a task era sua (ou de ninguem).
            largando = vazio and (
                atual in (None, "") or _mesmo_nome(atual, nome_chamador)
            )
            if not (pegando_para_si or largando):
                extras.add("atribuir_responsavel")

    return extras
