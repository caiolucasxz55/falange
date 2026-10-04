"""Modelo de dados do Falange V1.

Deliberadamente pequeno: task e nota. Sem epico, sem sprint. Essa e a
simplificacao em relacao ao Jira, nao uma etapa faltando.
"""

from enum import Enum as PyEnum
from typing import Optional

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Estimativa(str, PyEnum):
    PP = "PP"
    P = "P"
    M = "M"
    G = "G"


class Bloco(str, PyEnum):
    frontend = "frontend"
    backend = "backend"
    infra = "infra"
    seguranca = "seguranca"


class Prioridade(str, PyEnum):
    alta = "alta"
    media = "media"
    baixa = "baixa"


class Origem(str, PyEnum):
    """Quem escreveu a task. E o que permite medir a IA depois."""

    ia = "ia"
    humano = "humano"


class TipoDecisao(str, PyEnum):
    proxima_task = "proxima_task"
    prioridade = "prioridade"
    estimativa = "estimativa"
    quebrar_task = "quebrar_task"
    pre_task = "pre_task"
    # Nao vem de pergunta: o crud registra sozinho quando um humano corrige
    # um campo que a IA tinha escolhido.
    ajuste_humano = "ajuste_humano"


class OrigemPreferencia(str, PyEnum):
    explicita = "explicita"
    inferida = "inferida"


class Status(str, PyEnum):
    # Nao existe "bloqueada" aqui de proposito: bloqueio e representado por
    # bloqueada_por. Duas fontes de verdade para o mesmo fato divergem sempre.
    aberta = "aberta"
    em_andamento = "em_andamento"
    concluida = "concluida"


ABERTAS = (Status.aberta, Status.em_andamento)


class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(Text, default="")
    estimativa: Mapped[Estimativa] = mapped_column(Enum(Estimativa, name="estimativa"))
    bloco: Mapped[Bloco] = mapped_column(Enum(Bloco, name="bloco"))

    # Texto simples, nao FK para usuario. Multi-usuario/auth e V2.
    responsavel: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    # Auto-referencia: esta task esta travada POR outra task.
    bloqueada_por: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[Status] = mapped_column(
        Enum(Status, name="status"), default=Status.aberta
    )

    prioridade: Mapped[Prioridade] = mapped_column(
        Enum(Prioridade, name="prioridade"), default=Prioridade.media, index=True
    )

    # Default humano: so o MCP marca ia, entao task antiga nao vira da IA.
    origem: Mapped[Origem] = mapped_column(
        Enum(Origem, name="origem"), default=Origem.humano
    )

    # Marcos de tempo. O crud atualiza atualizada_em explicitamente em cada
    # escrita: sem trigger no banco, para a regra ficar visivel no codigo.
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Primeira ida para em_andamento; nao e sobrescrita depois.
    iniciada_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Volta a NULL se a task for reaberta.
    concluida_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Nota(Base):
    """Registro solto do time: problema, decisao ou duvida que precisa de mais
    gente. Existe para nao virar task bloqueada so para ser discutida."""

    __tablename__ = "nota"

    id: Mapped[int] = mapped_column(primary_key=True)
    texto: Mapped[str] = mapped_column(Text)

    # Texto simples, igual ao responsavel da task. Multi-usuario e V2.
    autor: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    # Nota pode nascer solta; se a task some, a nota sobrevive sem ela.
    task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task.id", ondelete="SET NULL"), nullable=True
    )

    resolvida: Mapped[bool] = mapped_column(Boolean, default=False)
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Configuracao(Base):
    """Chave/valor de comportamento da plataforma, editavel em runtime.

    Hoje guarda so `perguntas_ativas`: com ela desligada, a IA decide sozinha
    em vez de abrir opcoes. Tabela generica para nao precisar de migration a
    cada chave nova.
    """

    __tablename__ = "configuracao"

    chave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(String(200))
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Decisao(Base):
    """Uma escolha feita com opcoes: o que foi sugerido e o que foi escolhido.

    E a memoria do Falange. O modelo nao aprende entre sessoes; esta tabela
    aprende.
    """

    __tablename__ = "decisao"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoDecisao] = mapped_column(
        Enum(TipoDecisao, name="tipo_decisao"), index=True
    )
    sugerido: Mapped[dict] = mapped_column(JSONB)
    escolhido: Mapped[dict] = mapped_column(JSONB)
    aceita: Mapped[bool] = mapped_column(Boolean)
    motivo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsavel: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task.id", ondelete="SET NULL"), nullable=True
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Preferencia(Base):
    """Regra que o time quer que a IA siga.

    Explicita nasce ativa (alguem pediu). Inferida nasce inativa: padrao
    detectado nos dados so vale depois de um humano confirmar.
    """

    __tablename__ = "preferencia"

    id: Mapped[int] = mapped_column(primary_key=True)
    descricao: Mapped[str] = mapped_column(String(200))
    origem: Mapped[OrigemPreferencia] = mapped_column(
        Enum(OrigemPreferencia, name="origem_preferencia")
    )
    ativa: Mapped[bool] = mapped_column(Boolean, default=False)
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
