import asyncio
import shutil
import uuid
from pathlib import Path

from ferrum.operations.types import (
    FileOperation, OperationType, OperationStatus, ConflictResolution, ClipboardEntry
)


class OperationsManager:
    """Manages file operation queue and execution."""

    def __init__(self, on_progress=None, on_complete=None, on_error=None, on_conflict=None):
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        self.on_conflict = on_conflict
        self.clipboard: ClipboardEntry | None = None
        self._active: FileOperation | None = None

    def copy_to_clipboard(self, paths: list[str]) -> None:
        """Stage files for copying."""
        self.clipboard = ClipboardEntry(paths=paths, mode=OperationType.COPY)

    def cut_to_clipboard(self, paths: list[str]) -> None:
        """Stage files for moving."""
        self.clipboard = ClipboardEntry(paths=paths, mode=OperationType.MOVE)

    def clear_clipboard(self) -> None:
        self.clipboard = None

    async def paste(self, destination: str) -> FileOperation | None:
        """Execute a paste operation from clipboard."""
        if not self.clipboard:
            return None
        op = FileOperation(
            id=str(uuid.uuid4()),
            type=self.clipboard.mode,
            sources=list(self.clipboard.paths),
            destination=destination,
        )
        if self.clipboard.mode == OperationType.MOVE:
            self.clear_clipboard()
        await self._execute(op)
        return op

    async def delete(self, paths: list[str]) -> FileOperation:
        """Permanently delete files."""
        op = FileOperation(
            id=str(uuid.uuid4()),
            type=OperationType.DELETE,
            sources=paths,
            total_files=len(paths),
        )
        await self._execute(op)
        return op

    async def trash(self, paths: list[str]) -> FileOperation:
        """Move files to trash."""
        op = FileOperation(
            id=str(uuid.uuid4()),
            type=OperationType.TRASH,
            sources=paths,
            total_files=len(paths),
        )
        await self._execute(op)
        return op

    async def rename(self, src: str, dst: str) -> FileOperation:
        """Rename a file."""
        op = FileOperation(
            id=str(uuid.uuid4()),
            type=OperationType.RENAME,
            sources=[src],
            destination=dst,
            total_files=1,
        )
        await self._execute(op)
        return op

    async def mkdir(self, path: str) -> FileOperation:
        """Create a directory."""
        op = FileOperation(
            id=str(uuid.uuid4()),
            type=OperationType.MKDIR,
            sources=[],
            destination=path,
            total_files=1,
        )
        await self._execute(op)
        return op

    async def _execute(self, op: FileOperation) -> None:
        """Execute a file operation."""
        self._active = op
        op.status = OperationStatus.RUNNING
        op.total_files = len(op.sources)

        try:
            match op.type:
                case OperationType.COPY:
                    await self._execute_copy(op)
                case OperationType.MOVE:
                    await self._execute_move(op)
                case OperationType.DELETE:
                    await self._execute_delete(op)
                case OperationType.TRASH:
                    await self._execute_trash(op)
                case OperationType.RENAME:
                    await self._execute_rename(op)
                case OperationType.MKDIR:
                    await self._execute_mkdir(op)

            op.status = OperationStatus.COMPLETE
            op.progress = 1.0
            if self.on_complete:
                await self.on_complete(op)

        except Exception as e:
            op.status = OperationStatus.FAILED
            op.error = str(e)
            if self.on_error:
                await self.on_error(op)
        finally:
            self._active = None

    async def _resolve_conflict(self, op: FileOperation, dst: Path) -> ConflictResolution:
        """Ask the UI how to handle a conflict."""
        if op.conflict_resolution != ConflictResolution.ASK:
            return op.conflict_resolution
        if self.on_conflict:
            resolution = await self.on_conflict(str(dst))
            return resolution
        return ConflictResolution.SKIP

    async def _execute_copy(self, op: FileOperation) -> None:
        from ferrum.backends.router import is_smb_path
        dst_base = Path(op.destination)
        for i, src in enumerate(op.sources):
            src_path = Path(src)
            dst = dst_base / src_path.name
            op.current_file = src_path.name
            op.completed_files = i

            # Conflict resolution — only for local destinations
            if not is_smb_path(str(dst)) and dst.exists():
                resolution = await self._resolve_conflict(op, dst)
                if resolution == ConflictResolution.SKIP:
                    continue
                elif resolution == ConflictResolution.RENAME:
                    dst = self._unique_name(dst)

            src_is_smb = is_smb_path(src)
            dst_is_smb = is_smb_path(str(dst_base))

            if not src_is_smb and not dst_is_smb:
                # Local → Local
                if src_path.is_dir():
                    shutil.copytree(str(src_path), str(dst), dirs_exist_ok=True)
                else:
                    shutil.copy2(str(src_path), str(dst))
            else:
                # Cross-backend or SMB → SMB
                await asyncio.get_event_loop().run_in_executor(
                    None, self._cross_copy_file_sync, src, str(dst_base)
                )

            op.completed_files = i + 1
            op.progress = op.completed_files / op.total_files
            if self.on_progress:
                await self.on_progress(op)
            await asyncio.sleep(0)

    async def _execute_move(self, op: FileOperation) -> None:
        from ferrum.backends.router import is_smb_path
        dst_base = Path(op.destination)
        for i, src in enumerate(op.sources):
            src_path = Path(src)
            dst = dst_base / src_path.name
            op.current_file = src_path.name
            op.completed_files = i

            src_is_smb = is_smb_path(src)
            dst_is_smb = is_smb_path(str(dst_base))

            if not src_is_smb and not dst_is_smb:
                # Local → Local
                if dst.exists():
                    resolution = await self._resolve_conflict(op, dst)
                    if resolution == ConflictResolution.SKIP:
                        continue
                    elif resolution == ConflictResolution.RENAME:
                        dst = self._unique_name(dst)
                    elif resolution == ConflictResolution.OVERWRITE:
                        if dst.is_dir():
                            shutil.rmtree(str(dst))
                        else:
                            dst.unlink()
                shutil.move(str(src_path), str(dst))
            else:
                # Cross-backend: copy then delete source
                await asyncio.get_event_loop().run_in_executor(
                    None, self._cross_copy_file_sync, src, str(dst_base)
                )
                # Delete source after successful copy
                await asyncio.get_event_loop().run_in_executor(
                    None, self._cross_delete_sync, src
                )

            op.completed_files = i + 1
            op.progress = op.completed_files / op.total_files
            if self.on_progress:
                await self.on_progress(op)
            await asyncio.sleep(0)

    def _cross_copy_file_sync(self, src: str, dst_dir: str) -> None:
        """Copy a file between any combination of local and SMB paths."""
        import smbclient
        from ferrum.backends.router import is_smb_path, _find_username_for_host, KEYRING_SERVICE
        from ferrum.backends.smb import parse_smb_url, smb_path
        import keyring

        src_is_smb = is_smb_path(src)
        dst_is_smb = is_smb_path(dst_dir)

        filename = Path(src).name if not src_is_smb else src.rstrip("/").split("/")[-1]

        def _ensure_smb_session(host):
            username = _find_username_for_host(host)
            password = keyring.get_password(KEYRING_SERVICE, f"{username}@{host}") if username else None
            kwargs = {}
            if username:
                kwargs["username"] = username
            if password:
                kwargs["password"] = password
            try:
                smbclient.register_session(host, **kwargs)
            except Exception:
                pass

        CHUNK = 4 * 1024 * 1024  # 4MB chunks

        if src_is_smb and not dst_is_smb:
            # SMB → Local
            host, share, remaining = parse_smb_url(src)
            unc = smb_path(host, share, remaining)
            _ensure_smb_session(host)
            dst_path = Path(dst_dir) / filename
            with smbclient.open_file(unc, mode="rb") as src_f:
                with open(dst_path, "wb") as dst_f:
                    while True:
                        chunk = src_f.read(CHUNK)
                        if not chunk:
                            break
                        dst_f.write(chunk)

        elif not src_is_smb and dst_is_smb:
            # Local → SMB
            host, share, remaining = parse_smb_url(dst_dir)
            unc_dir = smb_path(host, share, remaining)
            unc_dst = unc_dir + "\\" + filename
            _ensure_smb_session(host)
            with open(src, "rb") as src_f:
                with smbclient.open_file(unc_dst, mode="wb") as dst_f:
                    while True:
                        chunk = src_f.read(CHUNK)
                        if not chunk:
                            break
                        dst_f.write(chunk)

        else:
            # SMB → SMB
            src_host, src_share, src_remaining = parse_smb_url(src)
            src_unc = smb_path(src_host, src_share, src_remaining)
            _ensure_smb_session(src_host)

            dst_host, dst_share, dst_remaining = parse_smb_url(dst_dir)
            dst_unc = smb_path(dst_host, dst_share, dst_remaining) + "\\" + filename
            _ensure_smb_session(dst_host)

            with smbclient.open_file(src_unc, mode="rb") as src_f:
                with smbclient.open_file(dst_unc, mode="wb") as dst_f:
                    while True:
                        chunk = src_f.read(CHUNK)
                        if not chunk:
                            break
                        dst_f.write(chunk)

    def _cross_delete_sync(self, path: str) -> None:
        """Delete a file or directory at a local or SMB path."""
        import smbclient
        from ferrum.backends.router import is_smb_path, _find_username_for_host, KEYRING_SERVICE
        from ferrum.backends.smb import parse_smb_url, smb_path
        import keyring

        if is_smb_path(path):
            host, share, remaining = parse_smb_url(path)
            unc = smb_path(host, share, remaining)
            username = _find_username_for_host(host)
            password = keyring.get_password(KEYRING_SERVICE, f"{username}@{host}") if username else None
            kwargs = {}
            if username:
                kwargs["username"] = username
            if password:
                kwargs["password"] = password
            try:
                smbclient.register_session(host, **kwargs)
            except Exception:
                pass
            if smbclient.path.isdir(unc):
                smbclient.rmdir(unc)
            else:
                smbclient.remove(unc)
        else:
            p = Path(path)
            if p.is_dir():
                shutil.rmtree(str(p))
            else:
                p.unlink()

    async def _execute_delete(self, op: FileOperation) -> None:
        for i, src in enumerate(op.sources):
            src_path = Path(src)
            op.current_file = src_path.name
            if src_path.is_dir():
                shutil.rmtree(str(src_path))
            else:
                src_path.unlink()
            op.completed_files = i + 1
            op.progress = op.completed_files / op.total_files
            if self.on_progress:
                await self.on_progress(op)
            await asyncio.sleep(0)

    async def _execute_trash(self, op: FileOperation) -> None:
        """Move files to XDG trash."""
        try:
            import send2trash
            for i, src in enumerate(op.sources):
                src_path = Path(src)
                op.current_file = src_path.name
                send2trash.send2trash(str(src_path))
                op.completed_files = i + 1
                op.progress = op.completed_files / op.total_files
                if self.on_progress:
                    await self.on_progress(op)
                await asyncio.sleep(0)
        except ImportError:
            # Fall back to manual XDG trash
            await self._execute_trash_manual(op)

    async def _execute_trash_manual(self, op: FileOperation) -> None:
        """Manual XDG trash implementation."""
        import time
        trash_dir = Path.home() / ".local" / "share" / "Trash"
        files_dir = trash_dir / "files"
        info_dir = trash_dir / "info"
        files_dir.mkdir(parents=True, exist_ok=True)
        info_dir.mkdir(parents=True, exist_ok=True)

        for i, src in enumerate(op.sources):
            src_path = Path(src)
            op.current_file = src_path.name
            dst = self._unique_name(files_dir / src_path.name)
            info_file = info_dir / f"{dst.name}.trashinfo"

            info_content = (
                f"[Trash Info]\n"
                f"Path={src_path}\n"
                f"DeletionDate={time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
            )
            info_file.write_text(info_content)
            shutil.move(str(src_path), str(dst))

            op.completed_files = i + 1
            op.progress = op.completed_files / op.total_files
            if self.on_progress:
                await self.on_progress(op)
            await asyncio.sleep(0)

    async def _execute_rename(self, op: FileOperation) -> None:
        src = Path(op.sources[0])
        dst = Path(op.destination)
        src.rename(dst)
        op.completed_files = 1
        op.progress = 1.0
        if self.on_progress:
            await self.on_progress(op)

    async def _execute_mkdir(self, op: FileOperation) -> None:
        Path(op.destination).mkdir(parents=True, exist_ok=True)
        op.completed_files = 1
        op.progress = 1.0
        if self.on_progress:
            await self.on_progress(op)

    def _unique_name(self, path: Path) -> Path:
        """Generate a unique filename by appending a number."""
        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1
        while True:
            new_path = parent / f"{stem} ({counter}){suffix}"
            if not new_path.exists():
                return new_path
            counter += 1