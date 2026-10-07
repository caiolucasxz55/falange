"""Contratos de entrada e saida da API."""

import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models import (
    Bloco,
    Estimativa,
    Origem,
    OrigemPreferencia,
    Prioridade,
    NivelAutonomia,
    Status,
    TipoAcao,
    TipoDecisao,
)


# Teto da descricao. O banco e Text (ilimitado), entao sem isto um loop
# enche o disco. Folgado para texto humano, apertado para abuso.
MAX_DESCRICAO = 5000

# Teto do JSON de uma decisao, serializado. Mesma razao: JSONB nao tem limite.
MAX_JSON_DECISAO = 4000


def _json_cabe(valor: dict, limite: int = MAX_JSON_DECISAO) -> dict:
    tamanho = len(json.dumps(valor, default=str))
    if tamanho > limite:
        raise ValueError(f"json com {tamanho} chars (maximo {limite})")
    return valor


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


class ConfiguracaoOut(BaseModel):
    """Comportamento da plataforma. Hoje so o interruptor das perguntas."""

    perguntas_ativas: bool


class ConfiguracaoEdicao(BaseModel):
    perguntas_ativas: Optional[bool] = None


class DecisaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: TipoDecisao
    sugerido: dict
    escolhido: dict
    aceita: bool
    motivo: Optional[str] = None
    responsavel: Optional[str] = None
    task_id: Optional[int] = None
    criada_em: datetime


class DecisaoNova(BaseModel):
    tipo: TipoDecisao
    sugerido: dict = Field(default_factory=dict)
    escolhido: dict = Field(default_factory=dict)

    _limitar = field_validator("sugerido", "escolhido")(_json_cabe)
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
