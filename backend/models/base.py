"""Base declarativa do SQLAlchemy.

Em modulo proprio para os modelos nao importarem uns aos outros so para
alcancar a Base, o que criaria ciclo assim que um modelo apontar para outro.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
