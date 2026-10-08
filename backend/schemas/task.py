"""Contratos de entrada e saida da task."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.models.enums import Bloco, Estimativa, Origem, Prioridade, Status
from backend.schemas.limites import MAX_DESCRICAO, recusar_nulos


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descricao: str
    estimativa: Estimativa
    bloco: Bloco
    responsavel: Optional[str] = None
    # O id e o fato; o texto acima e o rotulo de quem nao tem conta.
    responsavel_id: Optional[int] = None
    autor_id: Optional[int] = None
    bloqueada_por: Optional[int] = None
    status: Status
    prioridade: Prioridade
    criada_em: datetime
    atualizada_em: datetime
    iniciada_em: Optional[datetime] = None
    concluida_em: Optional[datetime] = None
    origem: Origem


class TaskNova(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)
    descricao: str = Field(default="", max_length=MAX_DESCRICAO)
    estimativa: Estimativa
    bloco: Bloco
    prioridade: Prioridade = Prioridade.media
    responsavel: Optional[str] = Field(default=None, max_length=80)
    # `origem` NAO entra aqui: e derivada do header X-Falange-Fonte pelo
    # backend. Deixar o cliente declarar quem escreveu a task permitiria
    # forjar autoria da IA e envenenar a calibracao e o perfil.


class TaskEdicao(BaseModel):
    """Edicao parcial: so os campos enviados sao alterados."""

    titulo: Optional[str] = Field(default=None, min_length=1, max_length=120)
    descricao: Optional[str] = Field(default=None, max_length=MAX_DESCRICAO)
    estimativa: Optional[Estimativa] = None
    bloco: Optional[Bloco] = None
    prioridade: Optional[Prioridade] = None
    responsavel: Optional[str] = Field(default=None, max_length=80)

    # `responsavel` fica de fora: null nele significa tirar o responsavel.
    _sem_nulos = model_validator(mode="before")(
        recusar_nulos("titulo", "descricao", "estimativa", "bloco", "prioridade")
    )


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
