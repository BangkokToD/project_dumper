from __future__ import annotations

from typing import Final

# Допустимые "не-буквенно-цифровые" символы токена (буквы/цифры — через str.isalnum()).
TOKEN_CHARS: Final[str] = "_-./*?[]"

# Символы, которые срезаем по краям кандидата (повторяющиеся тоже).
_TRIM_CHARS: Final[str] = "\"'`(){}<>,;:"


def _is_token_char(ch: str) -> bool:
    return ch.isalnum() or ch in TOKEN_CHARS


def _has_wildcard(token: str) -> bool:
    # В критерии "похож на путь" учитываем *, ?, [
    return ("*" in token) or ("?" in token) or ("[" in token)


def _has_extension(token: str) -> bool:
    """
    "Есть расширение" = после последней точки есть хотя бы одна буква.
    Примеры:
      - README.md -> True
      - v1.2.3 -> False (после последней точки только цифры)
      - pyproject.toml. -> False (после последней точки пусто)
    """
    if "." not in token:
        return False
    _, ext = token.rsplit(".", 1)
    if not ext:
        return False
    return any(ch.isalpha() for ch in ext)


def _is_forbidden(token: str) -> bool:
    low = token.lower()

    if token in {".", ".."}:
        return True

    if token.startswith("/"):
        return True

    if low.startswith("http://") or low.startswith("https://"):
        return True

    # "<letter>:"
    if len(token) >= 2 and token[0].isalpha() and token[1] == ":":
        return True

    if token.startswith("~/"):
        return True

    if token.startswith("./") or token.startswith("../"):
        return True

    if "//" in token:
        return True

    # path-segment "." / ".."
    for part in token.split("/"):
        if part in {".", ".."}:
            return True

    return False


def _normalize_candidate(raw: str) -> tuple[str, bool, bool]:
    """
    Возвращает:
      (token_after_trim_dot_slash, had_slash_before_tail_slash, had_wildcard_before_tail_slash)

    Порядок (как в ТЗ по смыслу):
      - trim
      - хвостовая точка (если есть "/" или wildcard или расширение ДО точки)
      - фиксируем признаки "похож на путь" ДО удаления хвостового "/"
      - хвостовой "/"
    """
    token = raw.strip(_TRIM_CHARS)
    if not token:
        return "", False, False

    # хвостовая точка: снимаем одну, если токен явно "похож на путь"
    # ("/" или wildcard или уже имеет расширение ДО точки)
    if token.endswith("."):
        token_wo_dot = token[:-1]
        if ("/" in token) or any(c in token for c in ("*", "?", "[", "]")) or _has_extension(token_wo_dot):
            token = token_wo_dot
            if not token:
                return "", False, False

    had_slash = "/" in token
    had_wildcard = _has_wildcard(token)

    # хвостовой "/": снимаем ровно один
    if token.endswith("/"):
        token = token[:-1]
        if not token:
            return "", had_slash, had_wildcard

    return token, had_slash, had_wildcard


def parse_list_tokens(text: str) -> list[str]:
    """
    Парсер токенов для вкладки "Список" (только строковая обработка, без ФС).
    """
    out: list[str] = []
    n = len(text)
    i = 0

    while i < n:
        if not _is_token_char(text[i]):
            i += 1
            continue

        start = i
        i += 1
        while i < n and _is_token_char(text[i]):
            i += 1
        end = i

        raw = text[start:end]
        token, had_slash, had_wildcard = _normalize_candidate(raw)
        if not token:
            continue

        # backslash-правило: смотрим СЫРОЙ кандидат (границы в исходном тексте)
        left = text[start - 1] if start > 0 else ""
        right = text[end] if end < n else ""
        if left == "\\" or right == "\\":
            continue

        if _is_forbidden(token):
            continue

        # "похож на путь"
        if not (had_slash or had_wildcard or _has_extension(token)):
            continue

        out.append(token)

    return out


# Backward-compat (если где-то уже использовалось старое имя)
parse_tokens = parse_list_tokens
