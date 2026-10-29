"""Consultas de usuario e sessao."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Papel, Sessao, TokenMCP, Usuario

# Email da conta de servico que o MCP usa. Tem de bater com a migration 0007.
EMAIL_IA = "falange-ia@falange.local"


def normalizar_email(email: str) -> str:
    """Minusculas e sem espaco nas pontas.

    Sem isto, "Caio@x " e "caio@x" viram duas contas para a mesma pessoa, e
    a unicidade do banco nao salva porque sao bytes diferentes.
    """
    return email.strip().lower()


async def buscar(session: AsyncSession, usuario_id: int) -> Optional[Usuario]:
    return await session.get(Usuario, usuario_id)


async def buscar_por_email(session: AsyncSession, email: str) -> Optional[Usuario]:
    q = select(Usuario).where(Usuario.email == normalizar_email(email))
    return (await session.scalars(q)).first()


async def buscar_conta_ia(session: AsyncSession) -> Optional[Usuario]:
    return await buscar_por_email(session, EMAIL_IA)


async def listar(
    session: AsyncSession, ativo: Optional[bool] = None
) -> list[Usuario]:
    q = select(Usuario).order_by(Usuario.nome, Usuario.id)
    if ativo is not None:
        q = q.where(Usuario.ativo == ativo)
    return list((await session.scalars(q)).all())


async def criar(session: AsyncSession, dados: dict) -> Usuario:
    dados = {**dados, "email": normalizar_email(dados["email"])}
    usuario = Usuario(**dados)
    session.add(usuario)
    await session.commit()
    await session.refresh(usuario)
    return usuario


async def editar(
    session: AsyncSession, usuario_id: int, campos: dict
) -> Optional[Usuario]:
    """Altera apenas os campos presentes. Rebaixar ou desativar corta as
    credenciais vivas (sessao e token de MCP) no mesmo commit: o efeito e
    imediato, nao no vencimento."""
    usuario = await session.get(Usuario, usuario_id)
    if usuario is None:
        return None

    if "email" in campos:
        campos = {**campos, "email": normalizar_email(campos["email"])}

    perdeu_poder = (
        "papel" in campos and campos["papel"] is not usuario.papel
    ) or campos.get("ativo") is False

    for campo, valor in campos.items():
        setattr(usuario, campo, valor)
    usuario.atualizado_em = func.now()

    if perdeu_poder:
        await _revogar_credenciais(session, usuario_id)

    await session.commit()
    await session.refresh(usuario)
    return usuario


async def buscar_por_nome(session: AsyncSession, nome: str) -> Optional[Usuario]:
    """Usuario cujo `nome` casa, ignorando caixa e espaco nas pontas.

    Devolve None quando ninguem casa E tambem quando mais de um casa: `nome`
    nao e unico, e escolher um dos dois no palpite gravaria a task na conta
    errada. Nesse caso o texto continua sendo o unico registro, que e
    exatamente o que ele existe para ser.
    """
    limpo = (nome or "").strip().lower()
    if not limpo:
        return None
    q = (
        select(Usuario)
        .where(func.lower(Usuario.nome) == limpo, Usuario.papel != Papel.ia)
        .limit(2)
    )
    achados = list((await session.scalars(q)).all())
    return achados[0] if len(achados) == 1 else None


async def existe_conta_humana(session: AsyncSession) -> bool:
    """Ja existe alguma conta de pessoa (qualquer papel, ativa ou nao)?

    Inativa conta: ela existe, e um admin pode reativa-la. O que importa aqui
    e saber se o banco ainda esta no estado de bootstrap.
    """
    q = select(Usuario.id).where(Usuario.papel != Papel.ia).limit(1)
    return (await session.scalars(q)).first() is not None


async def contar_por_papel(session: AsyncSession, papel: Papel) -> int:
    q = select(func.count(Usuario.id)).where(
        Usuario.papel == papel, Usuario.ativo.is_(True)
    )
    return int((await session.execute(q)).scalar_one())


# --------------------------------------------------------------------------
# sessao
# --------------------------------------------------------------------------


async def abrir_sessao(
    session: AsyncSession, usuario_id: int, refresh_hash: str, expira_em: datetime
) -> Sessao:
    sessao = Sessao(
        usuario_id=usuario_id, refresh_hash=refresh_hash, expira_em=expira_em
    )
    session.add(sessao)
    await session.commit()
    await session.refresh(sessao)
    return sessao


async def buscar_sessao(session: AsyncSession, sessao_id: int) -> Optional[Sessao]:
    return await session.get(Sessao, sessao_id)


async def buscar_sessao_por_refresh(
    session: AsyncSession, refresh_hash: str
) -> Optional[Sessao]:
    q = select(Sessao).where(Sessao.refresh_hash == refresh_hash)
    return (await session.scalars(q)).first()


def sessao_viva(sessao: Optional[Sessao], agora: Optional[datetime] = None) -> bool:
    """Sessao existe, nao foi revogada e nao venceu."""
    if sessao is None or sessao.revogada_em is not None:
        return False
    return sessao.expira_em > (agora or datetime.now(timezone.utc))


async def revogar_sessao(session: AsyncSession, sessao_id: int) -> bool:
    sessao = await session.get(Sessao, sessao_id)
    if sessao is None or sessao.revogada_em is not None:
        return False
    sessao.revogada_em = func.now()
    await session.commit()
    return True


async def girar_refresh(
    session: AsyncSession, sessao: Sessao, refresh_hash: str, expira_em: datetime
) -> Sessao:
    """Troca o refresh por um novo na mesma sessao.

    Girar a cada renovacao faz um refresh roubado valer uma vez so: quando o
    dono renova, o do ladrao para de existir.
    """
    sessao.refresh_hash = refresh_hash
    sessao.expira_em = expira_em
    sessao.usada_em = func.now()
    await session.commit()
    await session.refresh(sessao)
    return sessao


async def _revogar_sessoes(session: AsyncSession, usuario_id: int) -> None:
    """Corta todas as sessoes vivas do usuario. Nao commita."""
    await session.execute(
        update(Sessao)
        .where(Sessao.usuario_id == usuario_id, Sessao.revogada_em.is_(None))
        .values(revogada_em=func.now())
    )


async def _revogar_tokens_mcp(session: AsyncSession, usuario_id: int) -> None:
    """Corta os tokens de MCP vivos do usuario. Nao commita."""
    await session.execute(
        update(TokenMCP)
        .where(TokenMCP.usuario_id == usuario_id, TokenMCP.revogado_em.is_(None))
        .values(revogado_em=func.now())
    )


async def _revogar_credenciais(session: AsyncSession, usuario_id: int) -> None:
    """Corta TUDO com que a pessoa alcanca a API. Nao commita.

    Sessao da tela e token de MCP, juntos, porque sao a mesma pergunta:
    "esta pessoa ainda entra?". Cortar so a sessao deixava o token do MCP
    vivo -- e um notebook perdido tem o `.mcp.json` dentro dele, que e
    justamente o caso que este corte existe para resolver.
    """
    await _revogar_sessoes(session, usuario_id)
    await _revogar_tokens_mcp(session, usuario_id)


async def revogar_sessoes_do_usuario(session: AsyncSession, usuario_id: int) -> None:
    """Corta sessoes E tokens de MCP. O nome ficou da epoca em que so havia
    sessao; mudar ele mexeria na rota publica `/usuarios/{id}/sessoes`."""
    await _revogar_credenciais(session, usuario_id)
    await session.commit()
