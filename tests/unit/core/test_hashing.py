"""Hashing helper tests with known vectors."""

from pathlib import Path

from reprollm.core.hashing import is_text_file, sha256_bytes, sha256_file, sha256_text


def test_sha256_known_vectors() -> None:
    # sha256("abc") — well-known digest
    assert (
        sha256_bytes(b"abc")
        == "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert (
        sha256_bytes(b"")
        == "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_sha256_text_matches_bytes() -> None:
    assert sha256_text("abc") == sha256_bytes(b"abc")


def test_sha256_file_matches_bytes(tmp_path: Path) -> None:
    target = tmp_path / "f.bin"
    target.write_bytes(b"file content")
    assert sha256_file(target) == sha256_bytes(b"file content")


def test_sha256_file_chunked_matches(tmp_path: Path) -> None:
    payload = bytes(range(256)) * 1024  # 256 KiB, hashed with 1 KiB chunks
    target = tmp_path / "big.bin"
    target.write_bytes(payload)
    assert sha256_file(target, chunk_size=1024) == sha256_bytes(payload)


def test_is_text_file_accepts_utf8(tmp_path: Path) -> None:
    target = tmp_path / "t.txt"
    target.write_text("héllo wörld", encoding="utf-8")
    assert is_text_file(target, max_bytes=4096) is True


def test_is_text_file_rejects_nul(tmp_path: Path) -> None:
    target = tmp_path / "nul.bin"
    target.write_bytes(b"ab\x00cd")
    assert is_text_file(target, max_bytes=4096) is False


def test_is_text_file_rejects_undecodable(tmp_path: Path) -> None:
    target = tmp_path / "raw.bin"
    target.write_bytes(b"\xff\xd8\xff\xe0binaryjunk")
    assert is_text_file(target, max_bytes=4096) is False


def test_is_text_file_missing_is_false(tmp_path: Path) -> None:
    assert is_text_file(tmp_path / "missing.txt", max_bytes=4096) is False
