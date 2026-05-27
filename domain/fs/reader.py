from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from config.model import Config

try:
    from charset_normalizer import from_bytes
except Exception:
    from_bytes = None

_TEXT_CHARS = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))


@dataclass(slots=True)
class ReadTextResult:
    """Результат чтения текстового файла."""

    content: str | None
    skipped_reason: str | None = None
    error: str | None = None


_DEFAULT_CHUNK_SIZE = 1024 * 64


def is_binary_sample(b: bytes, threshold: float) -> bool:
    """
    Определить, является ли кусок байт бинарным.

    Args:
        b: Проба байт.
        threshold: Порог доли "нетекстовых" символов (0..1).

    Returns:
        True, если похоже на бинарник, иначе False.
    """
    if b"\x00" in b:
        return True
    if not b:
        return False
    nontext = sum(ch not in _TEXT_CHARS for ch in b)
    return (nontext / len(b)) > threshold


def read_text_file(p: Path, cfg: Config, chunk_size: int = _DEFAULT_CHUNK_SIZE) -> ReadTextResult:
    """Прочитать файл как текст и вернуть структурированный результат.

    Args:
        p: Путь к файлу.
        cfg: Текущий Config.
        chunk_size: Размер читаемого чанка в байтах.

    Returns:
        Структурированный результат чтения: текст, причина пропуска или ошибка.
    """
    try:
        size = p.stat().st_size
    except Exception as exc:
        return ReadTextResult(content=None, error=str(exc))

    if cfg.max_file_size and size > cfg.max_file_size:
        return ReadTextResult(
            content=None,
            skipped_reason=f"size {size} bytes > limit {cfg.max_file_size}",
        )

    effective_chunk_size = chunk_size if chunk_size > 0 else _DEFAULT_CHUNK_SIZE

    try:
        with p.open("rb") as fh:
            # Читаем первый кусок отдельно, чтобы проверить бинарность до полной загрузки.
            first_read = min(2048, effective_chunk_size)
            head = fh.read(first_read)

            if is_binary_sample(head, cfg.binary_threshold):
                return ReadTextResult(
                    content=None,
                    skipped_reason="binary content detected",
                )

            decoder_enc = cfg.encoding
            rest_size = max(0, effective_chunk_size - len(head))
            data = head + (fh.read(rest_size) if rest_size > 0 else b"")

            decoded_parts: list[str] = []
            decoded, decoder_enc, error = _decode_first_chunk(data, cfg, decoder_enc)
            if error is not None:
                return ReadTextResult(content=None, error=error)
            decoded_parts.append(decoded)

            while True:
                chunk = fh.read(effective_chunk_size)
                if not chunk:
                    break

                try:
                    decoded_parts.append(chunk.decode(decoder_enc, errors=cfg.errors_policy))
                except Exception:
                    try:
                        decoded_parts.append(chunk.decode(cfg.encoding, errors=cfg.errors_policy))
                    except Exception as exc:
                        return ReadTextResult(content=None, error=str(exc))

    except Exception as exc:
        return ReadTextResult(content=None, error=str(exc))

    return ReadTextResult(content="".join(decoded_parts))


def _decode_first_chunk(data: bytes, cfg: Config, decoder_enc: str) -> tuple[str, str, str | None]:
    """Декодировать первый блок данных с fallback на автоопределение кодировки.

    Args:
        data: Первый блок байт.
        cfg: Текущий Config.
        decoder_enc: Базовая кодировка из конфига.

    Returns:
        Кортеж ``(text, used_encoding, error)``. Если восстановиться не удалось,
        ``error`` содержит текст ошибки.
    """
    try:
        return data.decode(decoder_enc, errors=cfg.errors_policy), decoder_enc, None
    except Exception as initial_exc:
        if not cfg.detect_encoding or from_bytes is None:
            return "", decoder_enc, str(initial_exc)

    try:
        best = from_bytes(data).best()
        if best and best.encoding:
            detected_enc = str(best.encoding)
            return data.decode(detected_enc, errors=cfg.errors_policy), detected_enc, None
        return data.decode(cfg.encoding, errors=cfg.errors_policy), cfg.encoding, None
    except Exception as fallback_exc:
        return "", decoder_enc, str(fallback_exc)


def read_text_streaming(p: Path, cfg: Config, chunk_size: int = 1024 * 64) -> Iterable[str]:
    """
    Потоково читать текстовый файл с базовой защитой от бинарных данных и авто-детектом кодировки.

    Args:
        p: Путь к файлу.
        cfg: Текущий Config.
        chunk_size: Размер читаемого чанка (байт).

    Yields:
        Куски текста.
    """
    result = read_text_file(p, cfg, chunk_size=chunk_size)

    if result.content is not None:
        yield result.content
        return

    if result.skipped_reason is not None:
        yield f"[SKIPPED: {result.skipped_reason}]"
        return

    if result.error is not None:
        yield f"[ERROR: {result.error}]"
