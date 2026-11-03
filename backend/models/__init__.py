"""Modelo de dados do Falange, um arquivo por agregado.

Reexporta tudo para `from backend.models import X` seguir funcionando: o
alembic depende disso para ver todas as tabelas na Base, e um import que
esquecesse um modelo faria o autogenerate propor dropar a tabela.
"""

from backend.models.aprendizado import Autonomia, Decisao, Preferencia
from backend.models.base import Base
from backend.models.configuracao import Configuracao
from backend.models.criterio import (
    MAX_CRITERIOS,
    MAX_TEXTO_CRITERIO,
    MIN_CRITERIOS,
    MIN_TEXTO_CRITERIO,
    Criterio,
)
from backend.models.dependencia import Dependencia
from backend.models.evidencia import (
    MAX_REFERENCIA,
    MAX_RESUMO,
    MAX_SHA,
    MIN_SHA,
    Evidencia,
    TipoEvidencia,
)
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
from backend.models.marco import MAX_NOME as MAX_NOME_MARCO
from backend.models.marco import Marco
from backend.models.nota import Nota
from backend.models.projeto import SLUG_PADRAO, Projeto
from backend.models.task import Task
from backend.models.token_mcp import TokenMCP
from backend.models.usuario import Papel, Sessao, Usuario

__all__ = [
    "ABERTAS",
    "Autonomia",
    "Base",
    "Bloco",
    "Configuracao",
    "Criterio",
    "Decisao",
    "Dependencia",
    "Estimativa",
    "Evidencia",
    "MAX_CRITERIOS",
    "MAX_NOME_MARCO",
    "MAX_REFERENCIA",
    "MAX_RESUMO",
    "MAX_SHA",
    "MAX_TEXTO_CRITERIO",
    "MIN_CRITERIOS",
    "MIN_SHA",
    "MIN_TEXTO_CRITERIO",
    "NivelAutonomia",
    "Marco",
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
    "TipoEvidencia",
    "TokenMCP",
    "TipoDecisao",
    "Usuario",
]
