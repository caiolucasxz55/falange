"""Contratos de entrada e saida da task."""

from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# `MIN_CRITERIOS` nao e importado de proposito: aqui a lista vazia e
# aceita, para a tela (que ainda nao manda criterio) nao parar de criar
# task. O minimo de 1 e exigido pelo lint da pre-task, no MCP.
from backend.models.criterio import (
    MAX_CRITERIOS,
    MAX_TEXTO_CRITERIO,
    MIN_TEXTO_CRITERIO,
)
from backend.models.enums import Bloco, Estimativa, Origem, Prioridade, Status
from backend.schemas.limites import MAX_DESCRICAO, recusar_nulos
from backend.schemas.texto import NomeOpcional


class CriterioOut(BaseModel):
    """Um item do checklist de aceite da task."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    texto: str
    ordem: int
    # Nulo = nao verificado. Quem preenche e a Fase F, pela evidencia; nada
    # na E2 marca criterio como cumprido, nem a tela.
    cumprido_em: Optional[datetime] = None


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

    # Do grafo de dependencias, nao de coluna. `bloqueada` e DERIVADA de ter
    # dependencia nao concluida: nao ha estado para ficar desatualizado.
    depende_de: list[int] = Field(default_factory=list)
    travando: list[int] = Field(default_factory=list)
    bloqueada: bool = False

    # Como se sabe que a task acabou. Vazia nas tasks antigas em que a
    # migration 0010 nao achou a linha "Criterio de aceite:" na descricao.
    criterios: list[CriterioOut] = Field(default_factory=list)

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
    responsavel: NomeOpcional = None
    # `origem` NAO entra aqui: e derivada do header X-Falange-Fonte pelo
    # backend. Deixar o cliente declarar quem escreveu a task permitiria
    # forjar autoria da IA e envenenar a calibracao e o perfil.

    # De 1 a 5 criterios, 10 a 200 chars cada. O limite estrutural e aqui; se
    # o criterio e observavel ou so uma promessa e julgamento do lint da
    # pre-task, no MCP -- a API nao deve reprovar o texto de um humano na
    # tela por heuristica de prosa.
    #
    # O default vazio e por compatibilidade: a tela ainda nao manda criterio,
    # e exigir aqui derrubaria a criacao pela tela antes de ela aprender.
    criterios: list[str] = Field(
        default_factory=list,
        max_length=MAX_CRITERIOS,
    )

    @field_validator("criterios")
    @classmethod
    def _criterios_apresentaveis(cls, bruta: list[str]) -> list[str]:
        """Apara, descarta vazio e confere o tamanho de cada um.

        Aparar antes de medir e o que evita um criterio de espacos passar
        pelo minimo de 10 chars.
        """
        limpos = [c.strip() for c in bruta]
        limpos = [c for c in limpos if c]
        for texto in limpos:
            if not MIN_TEXTO_CRITERIO <= len(texto) <= MAX_TEXTO_CRITERIO:
                raise ValueError(
                    f"criterio com {len(texto)} chars; use de "
                    f"{MIN_TEXTO_CRITERIO} a {MAX_TEXTO_CRITERIO}: '{texto[:40]}'"
                )
        if len(limpos) > MAX_CRITERIOS:
            raise ValueError(f"no maximo {MAX_CRITERIOS} criterios por task")
        return limpos


class TaskEdicao(BaseModel):
    """Edicao parcial: so os campos enviados sao alterados."""

    titulo: Optional[str] = Field(default=None, min_length=1, max_length=120)
    descricao: Optional[str] = Field(default=None, max_length=MAX_DESCRICAO)
    estimativa: Optional[Estimativa] = None
    bloco: Optional[Bloco] = None
    prioridade: Optional[Prioridade] = None
    # Aparado, e vazio virando None: e assim que a tela e o MCP
    # removem o responsavel, com uma representacao so no banco.
    responsavel: NomeOpcional = None

    # `responsavel` fica de fora: null nele significa tirar o responsavel.
    _sem_nulos = model_validator(mode="before")(
        recusar_nulos("titulo", "descricao", "estimativa", "bloco", "prioridade")
    )


class DependenciaNova(BaseModel):
    """Uma aresta: esta task nao anda enquanto `depende_de` nao terminar."""

    depende_de: int


class MudancaStatus(BaseModel):
    status: Status


class Carga(BaseModel):
    escopo: str
    alvo: Optional[str]
    tasks_abertas: int
    limite: int
    sobrecarregado: bool
