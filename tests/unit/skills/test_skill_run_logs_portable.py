"""Bounded log context operates on complete in-memory lines on every platform."""

from __future__ import annotations

import hashlib
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"))
import skill_run_logs as logs  # noqa: E402


def test_complete_utf8_lines_keep_context_without_delivering_the_prefix():
    prefix = b"private preceding context\n"
    selected = "public 标签\n".encode()
    stream = io.BytesIO(prefix + selected)
    source = logs._Lines(stream, len(prefix + selected), len(prefix), lambda: None)
    sink = logs._Sink(source, selected=True)
    discarded = logs._Sink(source, selected=False)

    # A privacy recovery drain must not return any unfiltered source bytes.
    assert source.read() == "" and stream.tell() == 0
    for line in source:
        assert sink.write(line) == len(line)
        discarded.write(line)
    sink.flush()
    source.close()

    assert sink.parts == [selected.decode()]
    assert discarded.parts == []
    assert source.digest.hexdigest() == hashlib.sha256(prefix + selected).hexdigest()
    assert source.selected.hexdigest() == hashlib.sha256(selected).hexdigest()


@pytest.mark.parametrize("raw,limit", [(b"unfinished", 64), (b"abcde\n", 4)])
def test_partial_or_overlong_context_line_is_refused(monkeypatch, raw, limit):
    monkeypatch.setattr(logs, "MAX_LOG_BYTES", limit)
    source = logs._Lines(io.BytesIO(raw), len(raw), 0, lambda: None)
    with pytest.raises(logs.LogError, match="run_log_context_unproven"):
        next(source)


def test_offset_inside_a_multibyte_line_is_refused():
    raw = "标签\n".encode()
    source = logs._Lines(io.BytesIO(raw), len(raw), 1, lambda: None)
    with pytest.raises(logs.LogError, match="run_log_changed"):
        next(source)


def test_context_deadline_is_checked_before_consuming_a_line():
    stream = io.BytesIO(b"private context\n")

    def expired():
        raise logs.LogError("run_log_context_deadline")

    source = logs._Lines(stream, len(stream.getvalue()), 0, expired)
    with pytest.raises(logs.LogError, match="run_log_context_deadline"):
        next(source)
    assert stream.tell() == 0


def test_rendered_window_budget_counts_utf8_bytes_before_retaining_output(monkeypatch):
    monkeypatch.setattr(logs, "MAX_LOG_BYTES", 4)
    source = logs._Lines(io.BytesIO(), 0, 0, lambda: None)
    sink = logs._Sink(source, selected=True)
    assert sink.write("é" * 8) == 8
    with pytest.raises(logs.LogError, match="run_log_context_unproven"):
        sink.write("é")
    assert sink.parts == ["é" * 8]


@pytest.mark.parametrize("count", [0, 65_539])
def test_prefix_digest_is_exact_and_reads_bounded_chunks(count):
    class BoundedRead(io.BytesIO):
        def read(self, size=-1):
            assert 0 < size <= 65_536
            return super().read(size)

    raw = b"x" * 65_536 + b"tail beyond the selected prefix"
    stream = BoundedRead(raw)
    stream.seek(7)
    result = logs._digest_prefix(stream, count, lambda: None)
    assert result == hashlib.sha256(raw[:count]).hexdigest()
    assert stream.tell() == count


def test_prefix_digest_refuses_a_truncated_source():
    with pytest.raises(logs.LogError, match="run_log_changed"):
        logs._digest_prefix(io.BytesIO(b"short"), 6, lambda: None)


def test_prefix_digest_checks_the_deadline_before_reading():
    class Unreadable(io.BytesIO):
        def read(self, size=-1):
            pytest.fail("An expired context must not read more bytes")

    def expired():
        raise logs.LogError("run_log_context_deadline")

    with pytest.raises(logs.LogError, match="run_log_context_deadline"):
        logs._digest_prefix(Unreadable(b"private"), 7, expired)
