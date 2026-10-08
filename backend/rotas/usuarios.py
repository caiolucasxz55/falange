"""Rotas de usuario. Tudo aqui e `gerir_usuarios`, ou seja: so admin.

Nao existe DELETE. Apagar um usuario deixaria as tasks e decisoes dele
apontando para ninguem e apagaria a autoria do historico; desativar corta o
acesso na hora e preserva o que a pessoa fez. A unica excecao -- tirar o
ultimo admin ativo -- e barrada, porque ninguem sobraria para desfazer.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.models import Papel
from backend.repositorio import usuarios as repo
from backend.schemas.usuario import UsuarioEdicao, UsuarioNovo, UsuarioOut
from backend.seguranca import senha as mod_senha
from backend.seguranca.dependencias import Chamador, obter_chamador

rotas = APIRouter(tags=["usuarios"])


@rotas.get("/usuarios", response_model=list[UsuarioOut])
async def listar_usuarios(
    ativo: Optional[bool] = None,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("gerir_usuarios")
    return await repo.listar(session, ativo=ativo)


@rotas.post("/usuarios", response_model=UsuarioOut, status_code=201)
async def criar_usuario(
    novo: UsuarioNovo,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    chamador.exigir("gerir_usuarios")

    if novo.papel is Papel.ia:
        raise HTTPException(
            400,
            "papel 'ia' e da conta de servico: nao crie usuario com ele",
        )
    if await repo.buscar_por_email(session, novo.email) is not None:
        raise HTTPException(409, f"ja existe usuario com o email {novo.email}")

    return await repo.criar(
        session,
        {
            "email": novo.email,
            "nome": novo.nome,
            "senha_hash": mod_senha.gerar_hash(novo.senha),
            "papel": novo.papel,
        },
    )


@rotas.patch("/usuarios/{usuario_id}", response_model=UsuarioOut)
async def editar_usuario(
    usuario_id: int,
    body: UsuarioEdicao,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    """Muda nome, papel ou `ativo`. Rebaixar ou desativar corta as sessoes."""
    chamador.exigir("gerir_usuarios")

    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(400, "nenhum campo para alterar")

    alvo = await repo.buscar(session, usuario_id)
    if alvo is None:
        raise HTTPException(404, f"usuario {usuario_id} nao encontrado")

    if alvo.papel is Papel.ia:
        raise HTTPException(
            403, "a conta de servico falange-ia nao se edita pela API"
        )
    if campos.get("papel") is Papel.ia:
        raise HTTPException(400, "papel 'ia' e so da conta de servico")

    # Nao deixe a plataforma sem admin: sem ninguem com `gerir_usuarios`,
    # nao da para desfazer pela API.
    #
    # O schema recusa nulo explicito nestes campos, entao "esta em `campos`"
    # ja significa "veio um valor de verdade" -- sem isso, `{"papel": null}`
    # passava por aqui sem perde_admin e ia gravar NULL.
    perde_admin = alvo.papel is Papel.admin and (
        campos.get("ativo") is False
        or ("papel" in campos and campos["papel"] is not Papel.admin)
    )
    if perde_admin and await repo.contar_por_papel(session, Papel.admin) <= 1:
        raise HTTPException(
            409,
            "este e o ultimo admin ativo: promova outro antes de rebaixar ou desativar",
        )

    return await repo.editar(session, usuario_id, campos)


@rotas.delete("/usuarios/{usuario_id}/sessoes", status_code=204)
async def cortar_sessoes(
    usuario_id: int,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    """Derruba todas as sessoes de alguem, sem mexer na conta.

    E o que se usa quando um notebook e perdido: o acesso morre no request
    seguinte, nao no vencimento do token.
    """
    chamador.exigir("gerir_usuarios")

    if await repo.buscar(session, usuario_id) is None:
        raise HTTPException(404, f"usuario {usuario_id} nao encontrado")
    await repo.revogar_sessoes_do_usuario(session, usuario_id)
