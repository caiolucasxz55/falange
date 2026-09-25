"""Contratos de entrada e saida da API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.models import Bloco, Estimativa, Prioridade, Status


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descricao: str
    estimativa: Estimativa
    bloco: Bloco
    responsavel: Optional[str] = None
    bloqueada_por: Optional[int] = None
    status: Status
    prioridade: Prioridade
    criada_em: datetime
    atualizada_em: datetime
    iniciada_em: Optional[datetime] = None
    concluida_em: Optional[datetime] = None


class TaskNova(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)
    descricao: str = ""
    estimativa: Estimativa
    bloco: Bloco
    prioridade: Prioridade = Prioridade.media
    responsavel: Optional[str] = Field(default=None, max_length=80)


class TaskEdicao(BaseModel):
    """Edicao parcial: so os campos enviados sao alterados."""

    titulo: Optional[str] = Field(default=None, min_length=1, max_length=120)
    descricao: Optional[str] = None
    estimativa: Optional[Estimativa] = None
    bloco: Optional[Bloco] = None
    prioridade: Optional[Prioridade] = None
    responsavel: Optional[str] = Field(default=None, max_length=80)


class Bloqueio(BaseModel):
    # None = desbloquear. Um id = travada por aquela task.
    bloqueada_por: Optional[int] = None


class MudancaStatus(BaseModel):
    status: Status


class Carga(BaseModel):
    escopo: str
    alvo: Optional[str]
    tasks_abertas: int
    limite: int
    sobrecarregado: bool


class NotaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    texto: str
    autor: Optional[str] = None
    task_id: Optional[int] = None
    resolvida: bool
    criada_em: datetime


class NotaNova(BaseModel):
    texto: str = Field(min_length=5, max_length=2000)
    autor: Optional[str] = Field(default=None, max_length=80)
    task_id: Optional[int] = None


class NotaEdicao(BaseModel):
    """Edicao parcial da nota: so os campos enviados sao alterados.

    `resolvida` aqui tambem reabre uma nota fechada por engano.
    """

    texto: Optional[str] = Field(default=None, min_length=5, max_length=2000)
    autor: Optional[str] = Field(default=None, max_length=80)
    task_id: Optional[int] = None
    resolvida: Optional[bool] = None
