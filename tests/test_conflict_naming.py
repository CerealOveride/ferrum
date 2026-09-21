"""Tests for conflict rename helper on OperationsManager."""

from pathlib import Path

from ferrum.operations.manager import OperationsManager


def test_unique_name_appends_counter(tmp_path: Path):
    existing = tmp_path / "file.txt"
    existing.write_text("a")
    mgr = OperationsManager()
    unique = mgr._unique_name(existing)
    assert unique == tmp_path / "file (1).txt"
    assert not unique.exists()


def test_unique_name_skips_existing_counters(tmp_path: Path):
    (tmp_path / "doc.pdf").write_text("a")
    (tmp_path / "doc (1).pdf").write_text("b")
    mgr = OperationsManager()
    unique = mgr._unique_name(tmp_path / "doc.pdf")
    assert unique == tmp_path / "doc (2).pdf"


def test_unique_name_unchanged_when_free(tmp_path: Path):
    target = tmp_path / "free.txt"
    mgr = OperationsManager()
    assert mgr._unique_name(target) == target
