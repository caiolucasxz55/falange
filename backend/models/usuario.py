"""Usuario e sessao: o que torna autor e responsavel um fato, nao um texto.

`falange-ia` e uma conta de servico: existe como usuario de verdade, com
papel proprio, e entra pelo token compartilhado do MCP em vez de senha. E
o que permite as travas serem por papel e nao por header.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Papel(str, PyEnum):
    """Quem pode o que. A matriz mora em `dominio/papeis.py`.

    Os quatro primeiros sao uma escada de confianca; `ia` fica fora dela,
    porque uma conta de servico nao e uma pessoa com mais ou menos poder --
    e um papel com um recorte proprio.
    """

    admin = "admin"
    lead = "lead"
    dev = "dev"
    leitor = "leitor"
    ia = "ia"


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identidade de login. Unico e sempre guardado em minusculas, senao
    # "Caio@x" e "caio@x" viram duas contas para a mesma pessoa.
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(80))

    # Nulo na conta de servico: ela nao entra por login.
    senha_hash: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    papel: Mapped[Papel] = mapped_column(Enum(Papel, name="papel"))

    # Desligar em vez de apagar: as tasks e decisoes dela continuam
    # apontando para alguem que existiu. Inativo nao entra e nao renova.
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Sessao(Base):
    """Uma sessao viva de um usuario, para o refresh poder ser revogado.

    Sem esta tabela o JWT seria irrevogavel: logout, remocao de usuario e
    rebaixamento de papel so valeriam quando o token vencesse. Com ela, a
    API confere a cada request se a sessao ainda vale.
    """

    __tablename__ = "sessao"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), index=True
    )

    # So o hash do refresh. Vazamento da tabela nao da sessao a ninguem.
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Preenchido no logout ou quando um admin corta a sessao. Nao apagamos a
    # linha: saber que a sessao existiu e foi encerrada vale mais que o
    # espaco economizado.
    revogada_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    usada_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
