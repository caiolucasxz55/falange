"""Contratos de entrada e saida da nota."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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
