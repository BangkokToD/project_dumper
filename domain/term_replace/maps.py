from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from domain.term_replace.models import ReplacementRule

_REPLACEMENT_MAP_VERSION = 1


class ReplacementMapError(ValueError):
    """Контролируемая ошибка загрузки JSON-карты замен."""


@dataclass(slots=True)
class ReplacementMap:
    """JSON-карта замен найденных форм.

    Attributes:
        source_term: Базовый термин, по которому выполнялся поиск форм.
        rules: Правила замен по точным найденным формам.
        version: Версия формата карты замен.
    """

    source_term: str
    rules: list[ReplacementRule]
    version: int = _REPLACEMENT_MAP_VERSION


def replacement_map_to_json(replacement_map: ReplacementMap) -> str:
    """Сериализовать карту замен в стабильный JSON.

    Args:
        replacement_map: Карта замен.

    Returns:
        JSON-строка с предсказуемым порядком ключей.
    """
    data = {
        "version": replacement_map.version,
        "source_term": replacement_map.source_term,
        "rules": [
            {
                "source": rule.source,
                "replacement": rule.replacement,
                "enabled": rule.enabled,
            }
            for rule in replacement_map.rules
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def replacement_map_from_json(raw_json: str) -> ReplacementMap:
    """Загрузить и провалидировать JSON-карту замен.

    Args:
        raw_json: JSON-строка карты замен.

    Returns:
        Доменная карта замен.

    Raises:
        ReplacementMapError: Если JSON битый или структура карты невалидна.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ReplacementMapError(f"Некорректный JSON карты замен: {exc}") from exc

    if not isinstance(data, Mapping):
        raise ReplacementMapError("Карта замен должна быть JSON-объектом.")

    version = _required_int(data, "version")
    if version != _REPLACEMENT_MAP_VERSION:
        raise ReplacementMapError(
            f"Неподдерживаемая версия карты замен: {version}."
        )

    source_term = _required_str(data, "source_term")
    rules_raw = _required_list(data, "rules")

    rules: list[ReplacementRule] = []
    for index, item in enumerate(rules_raw):
        rules.append(_rule_from_json_item(item, index=index))

    return ReplacementMap(
        version=version,
        source_term=source_term,
        rules=rules,
    )


def _rule_from_json_item(item: object, *, index: int) -> ReplacementRule:
    """Преобразовать JSON-элемент правила в доменную модель.

    Args:
        item: Элемент массива ``rules``.
        index: Индекс элемента для понятной ошибки.

    Returns:
        Правило замены.

    Raises:
        ReplacementMapError: Если структура правила невалидна.
    """
    if not isinstance(item, Mapping):
        raise ReplacementMapError(
            f"Правило #{index + 1} должно быть JSON-объектом."
        )

    source = _required_str(item, "source", prefix=f"Правило #{index + 1}")
    replacement = _required_str(item, "replacement", prefix=f"Правило #{index + 1}")
    enabled = _optional_bool(item, "enabled", default=True)

    return ReplacementRule(
        source=source,
        replacement=replacement,
        enabled=enabled,
    )


def _required_str(
    data: Mapping[str, Any],
    key: str,
    *,
    prefix: str = "Карта замен",
) -> str:
    """Получить обязательную строку из JSON-объекта.

    Args:
        data: JSON-объект.
        key: Имя ключа.
        prefix: Префикс сообщения об ошибке.

    Returns:
        Значение ключа.

    Raises:
        ReplacementMapError: Если ключ отсутствует или значение не строка.
    """
    if key not in data:
        raise ReplacementMapError(f"{prefix}: отсутствует обязательный ключ `{key}`.")

    value = data[key]
    if not isinstance(value, str):
        raise ReplacementMapError(f"{prefix}: ключ `{key}` должен быть строкой.")

    return value


def _required_int(
    data: Mapping[str, Any],
    key: str,
    *,
    prefix: str = "Карта замен",
) -> int:
    """Получить обязательное целое число из JSON-объекта.

    Args:
        data: JSON-объект.
        key: Имя ключа.
        prefix: Префикс сообщения об ошибке.

    Returns:
        Значение ключа.

    Raises:
        ReplacementMapError: Если ключ отсутствует или значение не int.
    """
    if key not in data:
        raise ReplacementMapError(f"{prefix}: отсутствует обязательный ключ `{key}`.")

    value = data[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ReplacementMapError(f"{prefix}: ключ `{key}` должен быть целым числом.")

    return value


def _required_list(
    data: Mapping[str, Any],
    key: str,
    *,
    prefix: str = "Карта замен",
) -> list[object]:
    """Получить обязательный список из JSON-объекта.

    Args:
        data: JSON-объект.
        key: Имя ключа.
        prefix: Префикс сообщения об ошибке.

    Returns:
        Список значений.

    Raises:
        ReplacementMapError: Если ключ отсутствует или значение не список.
    """
    if key not in data:
        raise ReplacementMapError(f"{prefix}: отсутствует обязательный ключ `{key}`.")

    value = data[key]
    if not isinstance(value, list):
        raise ReplacementMapError(f"{prefix}: ключ `{key}` должен быть списком.")

    return value


def _optional_bool(
    data: Mapping[str, Any],
    key: str,
    *,
    default: bool,
    prefix: str = "Карта замен",
) -> bool:
    """Получить опциональное bool-значение из JSON-объекта.

    Args:
        data: JSON-объект.
        key: Имя ключа.
        default: Значение по умолчанию, если ключ отсутствует.
        prefix: Префикс сообщения об ошибке.

    Returns:
        Bool-значение.

    Raises:
        ReplacementMapError: Если значение ключа не bool.
    """
    if key not in data:
        return default

    value = data[key]
    if not isinstance(value, bool):
        raise ReplacementMapError(f"{prefix}: ключ `{key}` должен быть boolean.")

    return value