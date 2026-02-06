"""
Парсер "Список путей" (domain.list_scan.parser).

ВАЖНО: парсер должен быть чистым и не обращаться к файловой системе.

В этом коммите — только заготовка (без реализации, без тестов, без подключения).
Реализация будет в следующем шаге плана (Commit 3).
"""
from __future__ import annotations

"""
Парсер токенов для вкладки "Список" (без ФС).

Реализация строго по ТЗ v0.3.0, раздел 4.9.1:
  1) токенизация по алфавиту TOKEN_CHARS (Unicode буквы/цифры + символы)
  2) trim
  3) хвостовая точка
  4) хвостовой /
  5) backslash-правило (по исходному тексту)
  6) запрещённые формы
  7) "похож на путь"

Только строковая обработка. Без UI, без Path, без ФС.
"""

# В ТЗ: Unicode буквы/цифры + символы ниже.
TOKEN_CHARS: str = "_-./*?[]"

_TRIM_CHARS: frozenset[str] = frozenset(
    {
        "'",
        '"',
        "`",
        "(",
        ")",
        "{",
        "}",
        "<",
        ">",
        ",",
        ";",
        ":",
    }
)

# Для шага "хвостовая точка": в ТЗ перечислены * ? [ ]
_TAIL_DOT_WILDCARDS: frozenset[str] = frozenset({"*", "?", "[", "]"})

# Для "похож на путь": в ТЗ перечислены * ? [
_PATHLIKE_WILDCARDS: frozenset[str] = frozenset({"*", "?", "["})


def parse_tokens(text: str) -> list[str]:
    """
    Извлечь токены из произвольного текста.

    Токен = максимальный непрерывный фрагмент, где каждый символ принадлежит
    алфавиту токена (см. TOKEN_CHARS + Unicode буквы/цифры).
    Далее применяется нормализация/валидация по ТЗ.
    """
    tokens: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]
        if not _is_token_char(ch):
            i += 1
            continue

        start = i
        i += 1
        while i < n and _is_token_char(text[i]):
            i += 1
        end = i  # exclusive

        raw = text[start:end]
        token, start2, end2 = _normalize_with_span(raw, start, end)
        if not token:
            continue

        # 4.7: backslash-правило — по исходному тексту вокруг (уже) нормализованного кандидата
        if (start2 > 0 and text[start2 - 1] == "\\") or (end2 < n and text[end2] == "\\"):
            continue

        # 4.8: запрещённые формы
        if _is_forbidden(token):
            continue

        # 4.9: "похож на путь"
        if not _looks_like_path(token):
            continue

        tokens.append(token)

    return tokens


def normalize_token(token: str) -> str:
    """
    Нормализовать кандидат-токен (trim/хвостовые символы).

    Важно: backslash-правило зависит от исходного текста, поэтому делается в parse_tokens().
    """
    normalized, _, _ = _normalize_with_span(token, 0, len(token))
    return normalized


def _is_token_char(ch: str) -> bool:
    # Unicode буквы/цифры + спец-символы TOKEN_CHARS
    return ch.isalpha() or ch.isdigit() or (ch in TOKEN_CHARS)


def _normalize_with_span(token: str, start: int, end: int) -> tuple[str, int, int]:
    """
    Нормализация шага 4.5–4.6. Возвращает (token, start, end) с поправкой span'а
    относительно исходного текста (нужно для backslash-правила).
    """
    # 4.5 trim (убираем с краёв, повторяя, пока можно)
    while token and token[0] in _TRIM_CHARS:
        token = token[1:]
        start += 1
    while token and token[-1] in _TRIM_CHARS:
        token = token[:-1]
        end -= 1

    if not token:
        return "", start, end

    # 4.6 хвостовая точка: если токен заканчивается на "." и в нём есть "/" или wildcard (* ? [ ])
    if token.endswith(".") and ("/" in token or any(w in token for w in _TAIL_DOT_WILDCARDS)):
        token = token[:-1]
        end -= 1

    if not token:
        return "", start, end

    # 4.6 хвостовой "/": если заканчивается на "/", отрезать ровно один "/"
    if token.endswith("/"):
        token = token[:-1]
        end -= 1

    return token, start, end


def _is_forbidden(token: str) -> bool:
    if token in {".", ".."}:
        return True

    low = token.lower()

    # 4.8: начинается с "/"
    if token.startswith("/"):
        return True

    # 4.8: начинается с "http://" или "https://" (регистронезависимо)
    if low.startswith("http://") or low.startswith("https://"):
        return True

    # 4.8: начинается с "<буква>:"
    if len(token) >= 2 and token[0].isalpha() and token[1] == ":":
        return True

    # 4.8: начинается с "~/", "./", "../"
    if token.startswith("~/") or token.startswith("./") or token.startswith("../"):
        return True

    # 4.8: содержит "//" в любом месте
    if "//" in token:
        return True

    # 4.8: содержит path-segment "." или ".." (между "/")
    if "/" in token:
        for seg in token.split("/"):
            if seg in {".", ".."}:
                return True

    return False


def _looks_like_path(token: str) -> bool:
    # 4.9: содержит "/" ИЛИ wildcard (* ? [) ИЛИ расширение (после последней точки есть буква)
    if "/" in token:
        return True
    if any(w in token for w in _PATHLIKE_WILDCARDS):
        return True
    return _has_extension(token)


def _has_extension(token: str) -> bool:
    dot = token.rfind(".")
    if dot == -1 or dot == len(token) - 1:
        return False
    suffix = token[dot + 1 :]
    return any(ch.isalpha() for ch in suffix)
