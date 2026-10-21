"""Modelo de dados do Falange, um arquivo por agregado.

Reexporta tudo para `from backend.models import X` seguir funcionando: o
alembic depende disso para ver todas as tabelas na Base, e um import que
esquecesse um modelo faria o autogenerate propor dropar a tabela.
"""

from backend.models.aprendizado import Autonomia, Decisao, Preferencia
from backend.models.base import Base
from backend.models.configuracao import Configuracao
from backend.models.dependencia import Dependencia
from backend.models.enums import (
    ABERTAS,
    Bloco,
    Estimativa,
    NivelAutonomia,
    Origem,
    OrigemPreferencia,
    Prioridade,
    Status,
    TipoAcao,
    TipoDecisao,
)
from backend.models.nota import Nota
from backend.models.projeto import SLUG_PADRAO, Projeto
from backend.models.task import Task
from backend.models.usuario import Papel, Sessao, Usuario

__all__ = [
    "ABERTAS",
    "Autonomia",
    "Base",
    "Bloco",
    "Configuracao",
    "Decisao",
    "Dependencia",
    "Estimativa",
    "NivelAutonomia",
    "Nota",
    "Origem",
    "Papel",
    "OrigemPreferencia",
    "Preferencia",
    "Prioridade",
    "Projeto",
    "SLUG_PADRAO",
    "Sessao",
    "Status",
    "Task",
    "TipoAcao",
    "TipoDecisao",
    "Usuario",
]
