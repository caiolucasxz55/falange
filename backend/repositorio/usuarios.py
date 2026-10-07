"""Consultas de usuario e sessao."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Papel, Sessao, Usuario

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
    sessoes vivas no mesmo commit: o efeito e imediato, nao no vencimento."""
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
        await _revogar_sessoes(session, usuario_id)

    await session.commit()
    await session.refresh(usuario)
    return usuario


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


async def revogar_sessoes_do_usuario(session: AsyncSession, usuario_id: int) -> None:
    await _revogar_sessoes(session, usuario_id)
    await session.commit()
