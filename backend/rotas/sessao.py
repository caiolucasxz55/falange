"""Login, renovacao e logout.

O login e a unica rota que compara senha, e ela responde a mesma coisa para
email que nao existe e para senha errada: dizer qual dos dois falhou entrega
a lista de quem tem conta.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db import get_session
from backend.dominio.papeis import acoes_de
from backend.repositorio import usuarios as repo
from backend.schemas.usuario import (
    Eu,
    Login,
    Renovacao,
    SessaoAberta,
    TrocaDeSenha,
    UsuarioOut,
)
from backend.seguranca import senha as mod_senha
from backend.seguranca import sessao as mod_sessao
from backend.seguranca.dependencias import Chamador, obter_chamador

rotas = APIRouter(tags=["sessao"])

RECUSA = "email ou senha invalidos"


async def _abrir(session: AsyncSession, usuario) -> SessaoAberta:
    bruto, guardado = mod_sessao.gerar_refresh()
    sessao = await repo.abrir_sessao(
        session,
        usuario.id,
        guardado,
        mod_sessao.expira_em(settings.sessao_dias),
    )
    access = mod_sessao.criar_access(
        usuario.id,
        sessao.id,
        usuario.papel.value,
        settings.jwt_segredo,
        settings.jwt_minutos,
    )
    return SessaoAberta(
        access=access,
        refresh=bruto,
        expira_em_minutos=settings.jwt_minutos,
        usuario=UsuarioOut.model_validate(usuario),
    )


@rotas.post("/sessao", response_model=SessaoAberta, status_code=201)
async def entrar(body: Login, session: AsyncSession = Depends(get_session)):
    """Troca email e senha por um par access/refresh."""
    if not settings.jwt_segredo:
        raise HTTPException(503, "login desligado: JWT_SEGREDO nao configurado")

    usuario = await repo.buscar_por_email(session, body.email)
    # Mesma resposta nos tres casos, de proposito.
    if usuario is None or not usuario.ativo:
        raise HTTPException(401, RECUSA)

    confere, regravar = mod_senha.verificar(body.senha, usuario.senha_hash)
    if not confere:
        raise HTTPException(401, RECUSA)

    if regravar:
        # A biblioteca subiu os parametros: a senha vira um hash mais forte
        # agora, sem ninguem precisar trocar nada.
        await repo.editar(
            session, usuario.id, {"senha_hash": mod_senha.gerar_hash(body.senha)}
        )

    return await _abrir(session, usuario)


@rotas.post("/sessao/renovar", response_model=SessaoAberta)
async def renovar(body: Renovacao, session: AsyncSession = Depends(get_session)):
    """Troca um refresh valido por um par novo, girando o refresh.

    Girar faz um refresh roubado valer uma vez so: na renovacao seguinte do
    dono, o do ladrao deixa de existir.
    """
    if not settings.jwt_segredo:
        raise HTTPException(503, "login desligado: JWT_SEGREDO nao configurado")

    sessao = await repo.buscar_sessao_por_refresh(
        session, mod_sessao.hash_refresh(body.refresh)
    )
    if not repo.sessao_viva(sessao):
        raise HTTPException(401, "sessao encerrada ou expirada; entre de novo")

    usuario = await repo.buscar(session, sessao.usuario_id)
    if usuario is None or not usuario.ativo:
        raise HTTPException(401, "usuario inativo ou removido")

    bruto, guardado = mod_sessao.gerar_refresh()
    await repo.girar_refresh(
        session, sessao, guardado, mod_sessao.expira_em(settings.sessao_dias)
    )
    access = mod_sessao.criar_access(
        usuario.id,
        sessao.id,
        usuario.papel.value,
        settings.jwt_segredo,
        settings.jwt_minutos,
    )
    return SessaoAberta(
        access=access,
        refresh=bruto,
        expira_em_minutos=settings.jwt_minutos,
        usuario=UsuarioOut.model_validate(usuario),
    )


@rotas.delete("/sessao", status_code=204, response_class=Response)
async def sair(
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
    body: Optional[Renovacao] = None,
):
    """Encerra a sessao. Com o refresh no corpo, encerra aquela; sem ele,
    encerra todas as do chamador."""
    if chamador.usuario is None:
        raise HTTPException(401, "sem sessao para encerrar")

    if body is not None:
        sessao = await repo.buscar_sessao_por_refresh(
            session, mod_sessao.hash_refresh(body.refresh)
        )
        if sessao is not None and sessao.usuario_id == chamador.id:
            await repo.revogar_sessao(session, sessao.id)
            return
    await repo.revogar_sessoes_do_usuario(session, chamador.id)


@rotas.get("/eu", response_model=Eu)
async def eu(chamador: Chamador = Depends(obter_chamador)):
    """Quem a API acha que sou e o que eu alcanco.

    A tela chama isto para nao desenhar botao que vai dar 403.
    """
    return Eu(
        usuario=(
            UsuarioOut.model_validate(chamador.usuario) if chamador.usuario else None
        ),
        papel=chamador.papel,
        acoes=acoes_de(chamador.papel),
        sem_login=chamador.sem_login,
    )


@rotas.patch("/eu/senha", status_code=204, response_class=Response)
async def trocar_senha(
    body: TrocaDeSenha,
    chamador: Chamador = Depends(obter_chamador),
    session: AsyncSession = Depends(get_session),
):
    """Troca a propria senha. Exige a atual, e corta as outras sessoes."""
    if chamador.usuario is None:
        raise HTTPException(401, "faca login para trocar a senha")

    confere, _ = mod_senha.verificar(body.senha_atual, chamador.usuario.senha_hash)
    if not confere:
        raise HTTPException(403, "senha atual nao confere")

    recusa = mod_senha.senha_aceitavel(body.senha_nova)
    if recusa:
        raise HTTPException(400, recusa)

    # Trocar senha desloga todo lugar: e o que a pessoa espera de "trocar a
    # senha porque vazou". `editar` revoga quando o papel muda, nao aqui,
    # entao a revogacao e explicita.
    await repo.editar(
        session,
        chamador.usuario.id,
        {"senha_hash": mod_senha.gerar_hash(body.senha_nova)},
    )
    await repo.revogar_sessoes_do_usuario(session, chamador.usuario.id)
