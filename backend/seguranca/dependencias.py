"""Quem esta chamando, e pode fazer o que.

Tres portas chegam aqui, e a ordem importa:

1. **access token (JWT)** no `Authorization: Bearer` -- uma pessoa logada.
   A assinatura prova que ninguem forjou o token, mas o PAPEL vem do banco,
   nao do token: rebaixar ou desativar alguem tem efeito no request
   seguinte, nao no vencimento do token.
2. **token compartilhado + `X-Falange-Fonte: mcp`** -- a conta de servico
   `falange-ia`. E o que torna as travas da IA regra de papel em vez de
   checagem de header.
3. **token compartilhado sem o header** -- a tela antes de ter login. Com
   `EXIGIR_LOGIN=false` isto e tratado como admin sem login, que e o
   comportamento de antes da V2; com true, e 401.

O middleware ja barrou quem nao tem token nenhum. Aqui o assunto e
identidade, nao porta.
"""

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db import get_session
from backend.dominio import papeis
from backend.models import Papel, Usuario
from backend.repositorio import usuarios as repo
from backend.seguranca.sessao import ler_access
from backend.seguranca.token import FONTE_MCP, PREFIXO


class Chamador:
    """Quem fez o request.

    `usuario` e None so no caso 3 (tela sem login, EXIGIR_LOGIN=false), e
    ai `sem_login` e True e o papel e admin -- para a V1 nao quebrar durante
    a transicao. Todo o resto do codigo pergunta `pode(...)` e nao precisa
    saber por qual porta a pessoa entrou.
    """

    def __init__(
        self,
        usuario: Optional[Usuario],
        papel: Optional[str],
        sem_login: bool = False,
    ):
        self.usuario = usuario
        self.papel = papel
        self.sem_login = sem_login

    @property
    def id(self) -> Optional[int]:
        return self.usuario.id if self.usuario else None

    @property
    def nome(self) -> Optional[str]:
        """Nome de exibicao, usado para comparar com o campo `responsavel`.

        None sem login: ai nao da para provar que a pessoa e o responsavel
        que ela digitou, e atribuir passa a exigir permissao.
        """
        return self.usuario.nome if self.usuario else None

    @property
    def e_ia(self) -> bool:
        return self.papel == papeis.PAPEL_IA

    def pode(self, acao: str) -> bool:
        return papeis.pode(self.papel, acao)

    def exigir(self, acao: str) -> None:
        """Levanta 403 com uma mensagem que diz o que falta, nao so 'nao'."""
        if not self.pode(acao):
            if self.e_ia:
                raise HTTPException(
                    403,
                    f"a IA nao pode '{acao}': peca ao dev para fazer isso na tela",
                )
            raise HTTPException(
                403, f"papel '{self.papel}' nao pode '{acao}'"
            )

    def exigir_propria(self, acao: str, autor_id: Optional[int]) -> None:
        """Permite a acao ampla, ou a restrita quando o item e do chamador.

        E o caso do dev: apaga o que criou, nao o que o time criou.
        """
        if self.pode(acao):
            return
        restrita = f"{acao}_propria"
        if self.pode(restrita) and autor_id is not None and autor_id == self.id:
            return
        if self.pode(restrita):
            raise HTTPException(403, f"papel '{self.papel}' so pode {restrita}")
        self.exigir(acao)


async def _do_access(
    session: AsyncSession, cabecalho: str
) -> Optional[Chamador]:
    """Resolve um JWT. None quando o cabecalho nao carrega um JWT nosso."""
    if not settings.jwt_segredo:
        return None
    corpo = ler_access(cabecalho[len(PREFIXO) :], settings.jwt_segredo)
    if corpo is None:
        return None

    sessao = await repo.buscar_sessao(session, corpo["sessao_id"])
    if not repo.sessao_viva(sessao) or sessao.usuario_id != corpo["usuario_id"]:
        raise HTTPException(401, "sessao encerrada ou expirada; entre de novo")

    usuario = await repo.buscar(session, corpo["usuario_id"])
    if usuario is None or not usuario.ativo:
        raise HTTPException(401, "usuario inativo ou removido")

    # Papel do BANCO, nao do token.
    return Chamador(usuario, usuario.papel.value)


async def obter_chamador(
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_falange_fonte: Optional[str] = Header(default=None),
) -> Chamador:
    cabecalho = request.headers.get("authorization") or ""

    if cabecalho.startswith(PREFIXO):
        chamador = await _do_access(session, cabecalho)
        if chamador is not None:
            return chamador

    # Nao era JWT: e o token compartilhado, que o middleware ja validou.
    if x_falange_fonte == FONTE_MCP:
        conta = await repo.buscar_conta_ia(session)
        if conta is None or not conta.ativo:
            raise HTTPException(
                503, "conta de servico falange-ia ausente ou inativa; rode as migrations"
            )
        return Chamador(conta, conta.papel.value)

    # Transicao, e so para o bootstrap: o token compartilhado vale como admin
    # enquanto nao existe nenhuma conta humana. Depois da primeira, fecha --
    # senao bastaria apagar o cookie de sessao para virar admin.
    if papeis.admin_sem_login(
        settings.exigir_login, await repo.existe_conta_humana(session)
    ):
        return Chamador(None, Papel.admin.value, sem_login=True)

    raise HTTPException(
        401, "faca login: o token compartilhado nao identifica ninguem"
    )
