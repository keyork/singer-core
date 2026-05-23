from __future__ import annotations

from singer_core.progress import ProgressTracker


def test_load_returns_zero_when_no_file(tmp_path: object) -> None:
    tracker = ProgressTracker(str(tmp_path) + "/nonexistent.txt")  # type: ignore[arg-type]
    assert tracker.load() == 0


def test_save_and_load_roundtrip(tmp_path: object) -> None:
    fp = str(tmp_path) + "/progress.txt"  # type: ignore[arg-type]
    tracker = ProgressTracker(fp)
    tracker.save(42)
    assert tracker.load() == 42


def test_save_overwrites_previous(tmp_path: object) -> None:
    fp = str(tmp_path) + "/progress.txt"  # type: ignore[arg-type]
    tracker = ProgressTracker(fp)
    tracker.save(10)
    tracker.save(20)
    assert tracker.load() == 20


def test_reset_deletes_file(tmp_path: object) -> None:
    fp = str(tmp_path) + "/progress.txt"  # type: ignore[arg-type]
    tracker = ProgressTracker(fp)
    tracker.save(5)
    tracker.reset()
    assert tracker.load() == 0


def test_load_handles_corrupt_file(tmp_path: object) -> None:
    from pathlib import Path

    fp = Path(str(tmp_path)) / "progress.txt"  # type: ignore[arg-type]
    fp.write_text("not_a_number", encoding="utf-8")
    tracker = ProgressTracker(str(fp))
    assert tracker.load() == 0


def test_load_handles_empty_file(tmp_path: object) -> None:
    from pathlib import Path

    fp = Path(str(tmp_path)) / "progress.txt"  # type: ignore[arg-type]
    fp.write_text("", encoding="utf-8")
    tracker = ProgressTracker(str(fp))
    assert tracker.load() == 0
