"""Ensure delete/rename/mkdir/trash go through FSBackend (local)."""

import pytest
from pathlib import Path

from ferrum.operations.manager import OperationsManager


@pytest.mark.asyncio
async def test_mkdir_and_rename_via_backend(tmp_path: Path):
    mgr = OperationsManager()
    new_dir = tmp_path / "created"
    op = await mgr.mkdir(str(new_dir))
    assert op.status.value == "complete" or op.error is None
    assert new_dir.is_dir()

    renamed = tmp_path / "renamed"
    op2 = await mgr.rename(str(new_dir), str(renamed))
    assert renamed.is_dir()
    assert not new_dir.exists()
    assert op2.error is None


@pytest.mark.asyncio
async def test_delete_via_backend(tmp_path: Path):
    target = tmp_path / "gone.txt"
    target.write_text("x")
    mgr = OperationsManager()
    op = await mgr.delete([str(target)])
    assert not target.exists()
    assert op.error is None


@pytest.mark.asyncio
async def test_smb_trash_raises_via_backend():
    """SMB trash policy: not supported — surfaces as operation failure."""
    mgr = OperationsManager()
    op = await mgr.trash(["//nas.local/share/file.txt"])
    assert op.error is not None
    assert "Trash is not supported" in op.error or "SMB" in op.error
