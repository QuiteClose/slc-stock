import re

_SYMBOL_RE = re.compile(r"^[A-Za-z0-9.\-]{1,10}$")


def is_valid_symbol_format(symbol: str) -> bool:
    return bool(_SYMBOL_RE.match(symbol))
