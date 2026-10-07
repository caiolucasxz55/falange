"""Hash de senha com argon2.

Modulo puro: entra texto, sai texto ou bool. Sem sessao, sem HTTP.

argon2id e o padrao atual para senha: lento e com custo de memoria, o que
encarece ataque em GPU. Os parametros vem da biblioteca de proposito -- ela
acompanha a recomendacao melhor do que um numero chumbado aqui.

`verificar` tambem diz se o hash precisa ser refeito: quando a biblioteca
sobe os parametros, a senha antiga continua valendo e e regravada mais
forte no proximo login, sem ninguem precisar trocar nada.
"""

from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

# Senha curta nao vira forte com hash nenhum. Teto alto porque argon2 nao
# trunca (diferente do bcrypt), mas texto gigante e trabalho de graca.
MIN_SENHA = 10
MAX_SENHA = 200


def senha_aceitavel(senha: str) -> Optional[str]:
    """None se serve; a razao em texto se nao serve."""
    if len(senha) < MIN_SENHA:
        return f"senha curta: use pelo menos {MIN_SENHA} caracteres"
    if len(senha) > MAX_SENHA:
        return f"senha longa: no maximo {MAX_SENHA} caracteres"
    return None


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def verificar(senha: str, hash_guardado: Optional[str]) -> tuple[bool, bool]:
    """Devolve (confere, precisa_regravar).

    Hash ausente devolve (False, False): e o caso da conta de servico, que
    nao tem senha e nunca entra por login. Nao e erro, e recusa.
    """
    if not hash_guardado:
        return False, False
    try:
        _hasher.verify(hash_guardado, senha)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False
    return True, _hasher.check_needs_rehash(hash_guardado)
