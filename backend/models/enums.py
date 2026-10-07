"""Os valores fechados do dominio, em um lugar so.

Separados dos modelos porque o dominio puro, os schemas e as migrations
precisam deles sem precisar da tabela.
"""

from enum import Enum as PyEnum


class Estimativa(str, PyEnum):
    PP = "PP"
    P = "P"
    M = "M"
    G = "G"


class Bloco(str, PyEnum):
    frontend = "frontend"
    backend = "backend"
    infra = "infra"
    seguranca = "seguranca"


class Prioridade(str, PyEnum):
    alta = "alta"
    media = "media"
    baixa = "baixa"


class Origem(str, PyEnum):
    """Quem escreveu a task. E o que permite medir a IA depois."""

    ia = "ia"
    humano = "humano"


class TipoDecisao(str, PyEnum):
    proxima_task = "proxima_task"
    prioridade = "prioridade"
    estimativa = "estimativa"
    quebrar_task = "quebrar_task"
    pre_task = "pre_task"
    # Nao vem de pergunta: o repositorio registra sozinho quando um humano
    # corrige um campo que a IA tinha escolhido.
    ajuste_humano = "ajuste_humano"


class TipoAcao(str, PyEnum):
    """Acoes que podem ganhar autonomia.

    Apagar task e apagar nota NAO estao aqui de proposito: acao destrutiva
    nunca fica automatica, por melhor que seja o historico.
    """

    definir_prioridade = "definir_prioridade"
    definir_estimativa = "definir_estimativa"
    marcar_bloqueio = "marcar_bloqueio"
    criar_pre_tasks_aprovadas = "criar_pre_tasks_aprovadas"


class NivelAutonomia(str, PyEnum):
    # Pergunta a cada caso.
    perguntar = "perguntar"
    # Faz tudo e mostra um resumo para aprovar ou desfazer.
    confirmar_em_lote = "confirmar_em_lote"
    # Faz e so reporta no fim.
    automatico = "automatico"


class OrigemPreferencia(str, PyEnum):
    explicita = "explicita"
    inferida = "inferida"


class Status(str, PyEnum):
    # Nao existe "bloqueada" aqui de proposito: bloqueio e representado por
    # bloqueada_por. Duas fontes de verdade para o mesmo fato divergem sempre.
    aberta = "aberta"
    em_andamento = "em_andamento"
    concluida = "concluida"


ABERTAS = (Status.aberta, Status.em_andamento)
