from __future__ import annotations

import json

import pytest

from domain.term_replace.maps import (
    ReplacementMap,
    ReplacementMapError,
    replacement_map_from_json,
    replacement_map_to_json,
)
from domain.term_replace.models import ReplacementRule


def test_replacement_map_to_json_serializes_stable_structure() -> None:
    """Сериализует карту замен в стабильный JSON-формат."""
    replacement_map = ReplacementMap(
        source_term="супервайзер",
        rules=[
            ReplacementRule(
                source="Супервайзер",
                replacement="Руководитель",
                enabled=True,
            ),
            ReplacementRule(
                source="супервайзеру",
                replacement="руководителю",
                enabled=False,
            ),
        ],
    )

    raw_json = replacement_map_to_json(replacement_map)

    assert raw_json == (
        "{\n"
        '  "version": 1,\n'
        '  "source_term": "супервайзер",\n'
        '  "rules": [\n'
        "    {\n"
        '      "source": "Супервайзер",\n'
        '      "replacement": "Руководитель",\n'
        '      "enabled": true\n'
        "    },\n"
        "    {\n"
        '      "source": "супервайзеру",\n'
        '      "replacement": "руководителю",\n'
        '      "enabled": false\n'
        "    }\n"
        "  ]\n"
        "}"
    )


def test_replacement_map_from_json_loads_valid_map() -> None:
    """Загружает валидную JSON-карту замен."""
    raw_json = json.dumps(
        {
            "version": 1,
            "source_term": "супервайзер",
            "rules": [
                {
                    "source": "Супервайзер",
                    "replacement": "Руководитель",
                    "enabled": True,
                }
            ],
        },
        ensure_ascii=False,
    )

    replacement_map = replacement_map_from_json(raw_json)

    assert replacement_map.version == 1
    assert replacement_map.source_term == "супервайзер"
    assert replacement_map.rules == [
        ReplacementRule(
            source="Супервайзер",
            replacement="Руководитель",
            enabled=True,
        )
    ]


def test_replacement_map_from_json_ignores_extra_keys() -> None:
    """Игнорирует лишние ключи верхнего уровня и правил."""
    raw_json = json.dumps(
        {
            "version": 1,
            "source_term": "супервайзер",
            "rules": [
                {
                    "source": "Супервайзер",
                    "replacement": "Руководитель",
                    "enabled": False,
                    "occurrences": ["не должно попасть в модель"],
                }
            ],
            "files": ["README.md"],
            "preview": {"ignored": True},
        },
        ensure_ascii=False,
    )

    replacement_map = replacement_map_from_json(raw_json)

    assert replacement_map.source_term == "супервайзер"
    assert replacement_map.rules == [
        ReplacementRule(
            source="Супервайзер",
            replacement="Руководитель",
            enabled=False,
        )
    ]


def test_replacement_map_from_json_uses_enabled_true_for_old_rule_format() -> None:
    """Считает правило включённым, если старый формат не содержит enabled."""
    raw_json = json.dumps(
        {
            "version": 1,
            "source_term": "супервайзер",
            "rules": [
                {
                    "source": "Супервайзер",
                    "replacement": "Руководитель",
                }
            ],
        },
        ensure_ascii=False,
    )

    replacement_map = replacement_map_from_json(raw_json)

    assert replacement_map.rules == [
        ReplacementRule(
            source="Супервайзер",
            replacement="Руководитель",
            enabled=True,
        )
    ]


def test_replacement_map_from_json_rejects_broken_json() -> None:
    """Возвращает контролируемую ошибку при битом JSON."""
    with pytest.raises(ReplacementMapError, match="Некорректный JSON"):
        replacement_map_from_json("{ broken json")


@pytest.mark.parametrize(
    "raw_data",
    [
        [],
        "not object",
        123,
    ],
)
def test_replacement_map_from_json_rejects_non_object_root(raw_data: object) -> None:
    """Отклоняет JSON, если корень не объект."""
    with pytest.raises(ReplacementMapError, match="JSON-объектом"):
        replacement_map_from_json(json.dumps(raw_data, ensure_ascii=False))


@pytest.mark.parametrize(
    ("raw_data", "message"),
    [
        (
            {
                "source_term": "супервайзер",
                "rules": [],
            },
            "version",
        ),
        (
            {
                "version": 1,
                "rules": [],
            },
            "source_term",
        ),
        (
            {
                "version": 1,
                "source_term": "супервайзер",
            },
            "rules",
        ),
    ],
)
def test_replacement_map_from_json_rejects_missing_required_keys(
    raw_data: dict[str, object],
    message: str,
) -> None:
    """Отклоняет карту без обязательных верхнеуровневых ключей."""
    with pytest.raises(ReplacementMapError, match=message):
        replacement_map_from_json(json.dumps(raw_data, ensure_ascii=False))


@pytest.mark.parametrize(
    ("raw_data", "message"),
    [
        (
            {
                "version": "1",
                "source_term": "супервайзер",
                "rules": [],
            },
            "version",
        ),
        (
            {
                "version": 1,
                "source_term": 123,
                "rules": [],
            },
            "source_term",
        ),
        (
            {
                "version": 1,
                "source_term": "супервайзер",
                "rules": {},
            },
            "rules",
        ),
    ],
)
def test_replacement_map_from_json_rejects_invalid_root_value_types(
    raw_data: dict[str, object],
    message: str,
) -> None:
    """Отклоняет карту с неправильными типами верхнеуровневых значений."""
    with pytest.raises(ReplacementMapError, match=message):
        replacement_map_from_json(json.dumps(raw_data, ensure_ascii=False))


@pytest.mark.parametrize(
    ("rule", "message"),
    [
        (
            {
                "replacement": "Руководитель",
                "enabled": True,
            },
            "source",
        ),
        (
            {
                "source": "Супервайзер",
                "enabled": True,
            },
            "replacement",
        ),
        (
            {
                "source": 123,
                "replacement": "Руководитель",
                "enabled": True,
            },
            "source",
        ),
        (
            {
                "source": "Супервайзер",
                "replacement": 123,
                "enabled": True,
            },
            "replacement",
        ),
        (
            {
                "source": "Супервайзер",
                "replacement": "Руководитель",
                "enabled": "yes",
            },
            "enabled",
        ),
    ],
)
def test_replacement_map_from_json_rejects_invalid_rules(
    rule: dict[str, object],
    message: str,
) -> None:
    """Отклоняет правила без обязательных ключей или с неправильными типами."""
    raw_json = json.dumps(
        {
            "version": 1,
            "source_term": "супервайзер",
            "rules": [rule],
        },
        ensure_ascii=False,
    )

    with pytest.raises(ReplacementMapError, match=message):
        replacement_map_from_json(raw_json)


def test_replacement_map_from_json_rejects_non_object_rule() -> None:
    """Отклоняет правило, если оно не является JSON-объектом."""
    raw_json = json.dumps(
        {
            "version": 1,
            "source_term": "супервайзер",
            "rules": ["bad rule"],
        },
        ensure_ascii=False,
    )

    with pytest.raises(ReplacementMapError, match="Правило #1"):
        replacement_map_from_json(raw_json)


def test_replacement_map_from_json_rejects_unsupported_version() -> None:
    """Отклоняет неподдерживаемую версию карты."""
    raw_json = json.dumps(
        {
            "version": 2,
            "source_term": "супервайзер",
            "rules": [],
        },
        ensure_ascii=False,
    )

    with pytest.raises(ReplacementMapError, match="Неподдерживаемая версия"):
        replacement_map_from_json(raw_json)