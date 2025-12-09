from __future__ import annotations

from pathlib import Path

from project_dumper.config import Config
from project_dumper.reader import is_binary_sample, read_text_streaming


def test_is_binary_sample_text() -> None:
    data = b"hello world\njust ascii"
    assert is_binary_sample(data, threshold=0.3) is False


def test_is_binary_sample_with_null_byte() -> None:
    data = b"hello\x00world"
    assert is_binary_sample(data, threshold=0.3) is True


def test_read_text_streaming_small_text(tmp_path: Path) -> None:
    p = tmp_path / "file.txt"
    p.write_text("line1\nline2", encoding="utf-8")

    cfg = Config()
    chunks = list(read_text_streaming(p, cfg, chunk_size=8))
    text = "".join(chunks)
    assert "line1" in text
    assert "line2" in text


def test_read_text_streaming_respects_max_file_size(tmp_path: Path) -> None:
    p = tmp_path / "big.txt"
    p.write_text("x" * 1000, encoding="utf-8")

    cfg = Config()
    cfg.max_file_size = 10
    chunks = list(read_text_streaming(p, cfg, chunk_size=64))
    assert len(chunks) == 1
    assert "SKIPPED" in chunks[0]


def test_read_text_streaming_binary_detected(tmp_path: Path) -> None:
    p = tmp_path / "bin.bin"
    p.write_bytes(b"\x00\x01\x02\x03")

    cfg = Config()
    chunks = list(read_text_streaming(p, cfg, chunk_size=64))
    assert len(chunks) == 1
    assert "binary content detected" in chunks[0]
