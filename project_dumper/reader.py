from __future__ import annotations
from pathlib import Path
from typing import Iterable
from .config import Config

try:
    from charset_normalizer import from_bytes
except Exception:
    from_bytes = None

_TEXT_CHARS = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)))

def is_binary_sample(b: bytes, threshold: float) -> bool:
    if b"\x00" in b:
        return True
    if not b:
        return False
    nontext = sum(ch not in _TEXT_CHARS for ch in b)
    return (nontext / len(b)) > threshold

def read_text_streaming(p: Path, cfg: Config, chunk_size: int = 1024 * 64) -> Iterable[str]:
    size = p.stat().st_size
    if cfg.max_file_size and size > cfg.max_file_size:
        yield f"[SKIPPED: size {size} bytes > limit {cfg.max_file_size}]"
        return
    with p.open("rb") as fh:
        head = fh.read(2048)
        if is_binary_sample(head, cfg.binary_threshold):
            yield "[SKIPPED: binary content detected]"
            return
        # Определяем кодировку: сначала заданная, при неудаче — авто
        decoder_enc = cfg.encoding
        data = head + fh.read(chunk_size - len(head))
        # пробуем заданную
        try:
            text = data.decode(decoder_enc, errors=cfg.errors_policy)
            yield text
        except Exception:
            if cfg.detect_encoding and from_bytes is not None:
                best = from_bytes(data).best()
                if best:
                    decoder_enc = str(best.encoding)
                    yield best.output()
                else:
                    yield data.decode(cfg.encoding, errors=cfg.errors_policy)
            else:
                yield data.decode(cfg.encoding, errors=cfg.errors_policy)
        # дальше потоково
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            try:
                yield chunk.decode(decoder_enc, errors=cfg.errors_policy)
            except Exception:
                yield chunk.decode(cfg.encoding, errors=cfg.errors_policy)
