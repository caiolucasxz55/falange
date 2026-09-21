"""Contratos de entrada e saida da API."""

from typing import Optional

from pydantic import BaseModel, ConfigDict

from backend.models import Bloco, Estimativa, Status


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


class TaskNova(BaseModel):
    titulo: str
    descricao: str = ""
    estimativa: Estimativa
    bloco: Bloco
    responsavel: Optional[str] = None


class TaskEdicao(BaseModel):
    """Edicao parcial: so os campos enviados sao alterados."""

    titulo: Optional[str] = None
    descricao: Optional[str] = None
    estimativa: Optional[Estimativa] = None
    bloco: Optional[Bloco] = None
    responsavel: Optional[str] = None


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
