"""Contratos da configuracao da plataforma."""

from typing import Optional

from pydantic import BaseModel


class ConfiguracaoOut(BaseModel):
    """Comportamento da plataforma. Hoje so o interruptor das perguntas."""

    perguntas_ativas: bool


class ConfiguracaoEdicao(BaseModel):
    perguntas_ativas: Optional[bool] = None
