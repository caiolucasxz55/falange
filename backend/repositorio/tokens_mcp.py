"""Consultas e escritas do token de conexao do MCP.

Como no resto do pacote: nao levanta `HTTPException`. Devolve `None`,
`False` ou `(valor, erro)` e deixa a rota traduzir para HTTP.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import TokenMCP


def token_vivo(
    token: Optional[TokenMCP], agora: Optional[datetime] = None
) -> bool:
    """Token existe, nao foi revogado e nao venceu.

    Espelha `usuarios.sessao_viva`, com uma diferenca: aqui `expira_em`
    pode ser nulo, e nulo significa "vale ate revogar".
    """
    if token is None or token.revogado_em is not None:
        return False
    if token.expira_em is None:
        return True
    return token.expira_em > (agora or datetime.now(timezone.utc))


async def criar(
    session: AsyncSession,
    usuario_id: int,
    projeto_id: int,
    nome: str,
    prefixo: str,
    hash_segredo: str,
    expira_em: Optional[datetime] = None,
) -> TokenMCP:
    token = TokenMCP(
        usuario_id=usuario_id,
        projeto_id=projeto_id,
        nome=nome,
        prefixo=prefixo,
        hash_segredo=hash_segredo,
        expira_em=expira_em,
    )
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


async def buscar_por_prefixo(
    session: AsyncSession, prefixo: str
) -> Optional[TokenMCP]:
    """A linha do token, achada pelo pedaco publico dele.

    E isto que o prefixo existe para permitir: um SELECT por indice unico,
    em vez de hashear o segredo contra todas as linhas da tabela.
    """
    q = select(TokenMCP).where(TokenMCP.prefixo == prefixo)
    return (await session.scalars(q)).first()


async def listar_do_usuario(
    session: AsyncSession, usuario_id: int, incluir_revogados: bool = False
) -> list[TokenMCP]:
    q = select(TokenMCP).where(TokenMCP.usuario_id == usuario_id)
    if not incluir_revogados:
        q = q.where(TokenMCP.revogado_em.is_(None))
    # Mais recente primeiro: o que a pessoa acabou de criar e o que ela
    # esta procurando na tela.
    return list((await session.scalars(q.order_by(TokenMCP.criado_em.desc()))).all())


async def revogar(
    session: AsyncSession, token_id: int, usuario_id: Optional[int] = None
) -> bool:
    """False quando o token nao existe, nao e da pessoa, ou ja foi revogado.

    `usuario_id` None e o caso do admin, que alcanca o token de qualquer
    um pela permissao `gerir_usuarios`. Com um id, so o proprio dono passa
    -- e por isso que a rota de `/eu` sempre manda o id.
    """
    token: Optional[TokenMCP] = await session.get(TokenMCP, token_id)
    if token is None or token.revogado_em is not None:
        return False
    if usuario_id is not None and token.usuario_id != usuario_id:
        return False

    token.revogado_em = datetime.now(timezone.utc)
    await session.commit()
    return True


async def marcar_uso(session: AsyncSession, token_id: int) -> None:
    """Anota que o token acabou de ser usado.

    Commit proprio e curto: roda em TODA chamada autenticada por token, e
    nao deve participar da transacao da rota -- uma falha depois disto nao
    pode desfazer o registro de que a credencial foi usada.
    """
    token: Optional[TokenMCP] = await session.get(TokenMCP, token_id)
    if token is None:
        return
    token.ultimo_uso_em = datetime.now(timezone.utc)
    await session.commit()


async def revogar_do_usuario(session: AsyncSession, usuario_id: int) -> int:
    """Corta todos os tokens vivos de uma pessoa. Devolve quantos cortou.

    Chamado quando a conta e desativada ou rebaixada: a sessao da tela ja
    e cortada nesse caso, e deixar o token do MCP vivo seria uma porta
    aberta exatamente para quem acabou de perder o acesso.
    """
    q = select(TokenMCP).where(
        TokenMCP.usuario_id == usuario_id, TokenMCP.revogado_em.is_(None)
    )
    agora = datetime.now(timezone.utc)
    cortados = 0
    for token in (await session.scalars(q)).all():
        token.revogado_em = agora
        cortados += 1
    if cortados:
        await session.commit()
    return cortados
