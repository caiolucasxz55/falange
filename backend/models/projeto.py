"""Projeto: o contexto a que uma task, nota ou regra pertence.

Existe para o Falange poder guardar o proprio backlog sem misturar com dado
de verificacao. Sem isso, testar o sistema ponta a ponta cria e apaga linhas
no mesmo banco onde esta o trabalho real.

O que e por projeto: task, nota, decisao, preferencia, configuracao e
autonomia. Confianca e ajuste valem para UM contexto -- a IA ter ganhado
autonomia num projeto nao diz nada sobre outro.

O que e global: usuario e sessao. Papel por projeto esta fora da V2.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

# Projeto que recebe tudo o que existia antes da migration, e o usado quando
# a chamada nao diz em qual projeto esta.
SLUG_PADRAO = "padrao"

# Slug: minusculas, digitos e hifen; nao comeca nem termina com hifen. E o
# que vai no header e na env do MCP, entao precisa ser curto e sem surpresa.
PADRAO_SLUG = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"
MAX_SLUG = 40
MAX_NOME_PROJETO = 80


class Projeto(Base):
    __tablename__ = "projeto"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(MAX_SLUG), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(MAX_NOME_PROJETO))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
