"""Contratos de entrada e saida do marco."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.models.marco import MAX_NOME
from backend.schemas.limites import recusar_nulos

MIN_NOME = 2


class MarcoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    data_alvo: Optional[date] = None
    fechado_em: Optional[datetime] = None
    criado_em: datetime


class MarcoComPrevisao(MarcoOut):
    """O marco com o veredito de prazo junto.

    `previsao` vem de `dominio/previsao.py` e carrega a CONTA: dias de
    trabalho restante, dias de calendario e o detalhe por classe. Sai como
    dict porque e saida de dominio puro -- dar um schema a ela aqui faria
    o contrato da API dever obediencia ao formato interno do calculo.
    """

    previsao: dict


class MarcoNovo(BaseModel):
    nome: str = Field(min_length=MIN_NOME, max_length=MAX_NOME)
    # Nulo = marco sem prazo. A previsao devolve `sem_data` nesse caso, em
    # vez de fingir um veredito.
    data_alvo: Optional[date] = None

    @field_validator("nome")
    @classmethod
    def _aparar(cls, bruto: str) -> str:
        limpo = bruto.strip()
        if len(limpo) < MIN_NOME:
            raise ValueError(f"nome do marco: pelo menos {MIN_NOME} chars")
        return limpo


class MarcoEdicao(BaseModel):
    """Edicao parcial: so os campos enviados sao alterados."""

    nome: Optional[str] = Field(default=None, min_length=MIN_NOME, max_length=MAX_NOME)
    data_alvo: Optional[date] = None

    @field_validator("nome")
    @classmethod
    def _aparar(cls, bruto: Optional[str]) -> Optional[str]:
        """Apara antes de medir, como `MarcoNovo`.

        Sem isto, `PATCH` com "  a  " gravava um nome de 1 char com
        espacos -- que `POST` recusaria. Duas portas para o mesmo campo
        com regras diferentes e como o dado invalido entra.
        """
        if bruto is None:
            return None
        limpo = bruto.strip()
        if len(limpo) < MIN_NOME:
            raise ValueError(f"nome do marco: pelo menos {MIN_NOME} chars")
        return limpo

    # `data_alvo` fica de fora: null nele significa TIRAR o prazo, que e
    # uma operacao legitima -- mesma convencao de `responsavel` na task.
    _sem_nulos = model_validator(mode="before")(recusar_nulos("nome"))


class FechamentoMarco(BaseModel):
    fechado: bool
