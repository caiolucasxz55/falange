"""Contratos de entrada e saida da API, um arquivo por agregado.

Reexporta tudo para `from backend.schemas import X` seguir funcionando.
"""

from backend.schemas.aprendizado import (
    AutonomiaEdicao,
    DecisaoNova,
    DecisaoOut,
    PreferenciaEdicao,
    PreferenciaNova,
    PreferenciaOut,
)
from backend.schemas.configuracao import ConfiguracaoEdicao, ConfiguracaoOut
from backend.schemas.limites import MAX_DESCRICAO, MAX_JSON_DECISAO, json_cabe
from backend.schemas.nota import NotaEdicao, NotaNova, NotaOut
from backend.schemas.usuario import (
    Email,
    Eu,
    Login,
    Renovacao,
    SessaoAberta,
    TrocaDeSenha,
    UsuarioEdicao,
    UsuarioNovo,
    UsuarioOut,
)
from backend.schemas.task import (
    Bloqueio,
    Carga,
    MudancaStatus,
    TaskEdicao,
    TaskNova,
    TaskOut,
)

__all__ = [
    "MAX_DESCRICAO",
    "MAX_JSON_DECISAO",
    "AutonomiaEdicao",
    "Bloqueio",
    "Carga",
    "ConfiguracaoEdicao",
    "ConfiguracaoOut",
    "DecisaoNova",
    "DecisaoOut",
    "MudancaStatus",
    "NotaEdicao",
    "NotaNova",
    "NotaOut",
    "PreferenciaEdicao",
    "PreferenciaNova",
    "PreferenciaOut",
    "TaskEdicao",
    "TaskNova",
    "TaskOut",
    "Email",
    "Eu",
    "Login",
    "Renovacao",
    "SessaoAberta",
    "TrocaDeSenha",
    "UsuarioEdicao",
    "UsuarioNovo",
    "UsuarioOut",
    "json_cabe",
]
