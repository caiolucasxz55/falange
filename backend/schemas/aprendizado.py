"""Contratos de decisao, preferencia e autonomia."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models.enums import NivelAutonomia, OrigemPreferencia, TipoDecisao
from backend.schemas.limites import json_cabe


class DecisaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: TipoDecisao
    sugerido: dict
    escolhido: dict
    aceita: bool
    motivo: Optional[str] = None
    responsavel: Optional[str] = None
    autor_id: Optional[int] = None
    task_id: Optional[int] = None
    criada_em: datetime


class DecisaoNova(BaseModel):
    tipo: TipoDecisao
    sugerido: dict = Field(default_factory=dict)
    escolhido: dict = Field(default_factory=dict)

    _limitar = field_validator("sugerido", "escolhido")(json_cabe)
    aceita: bool
    motivo: Optional[str] = Field(default=None, max_length=500)
    responsavel: Optional[str] = Field(default=None, max_length=80)
    task_id: Optional[int] = None


class PreferenciaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao: str
    origem: OrigemPreferencia
    ativa: bool
    criada_em: datetime


class PreferenciaNova(BaseModel):
    descricao: str = Field(min_length=5, max_length=200)
    origem: OrigemPreferencia


class PreferenciaEdicao(BaseModel):
    ativa: bool


class AutonomiaEdicao(BaseModel):
    nivel: NivelAutonomia
