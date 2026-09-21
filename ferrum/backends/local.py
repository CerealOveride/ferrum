import os
import aiofiles.os
from datetime import datetime
from pathlib import Path

from ferrum.backends.base import FSBackend, FileEntry


class LocalBackend(FSBackend):
    """Backend for local filesystem access."""

    async def list_dir(self, path: str) -> list[FileEntry]:
        """List contents of a directory asynchronously."""
        entries = []
        expanded = str(Path(path).expanduser().resolve())

        try:
            scan = await aiofiles.os.scandir(expanded)
            for entry in scan:
                try:
                    stat = entry.stat(follow_symlinks=False)
                    is_symlink = entry.is_symlink()
                    is_dir = entry.is_dir(follow_symlinks=True)
                    name = entry.name
                    extension = "" if is_dir else Path(name).suffix.lower()

                    entries.append(FileEntry(
                        name=name,
                        path=entry.path,
                        is_dir=is_dir,
                        size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        is_hidden=name.startswith("."),
                        is_symlink=is_symlink,
                        extension=extension,
                    ))
                except (PermissionError, OSError):
                    # Skip entries we can't stat
                    continue
        except PermissionError:
            raise PermissionError(f"Permission denied: {expanded}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Directory not found: {expanded}")

        # Directories first, then files, both alphabetical
        entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return entries

    async def stat(self, path: str) -> FileEntry:
        expanded = str(Path(path).expanduser().resolve())
        stat = await aiofiles.os.stat(expanded)
        p = Path(expanded)
        is_dir = p.is_dir()
        return FileEntry(
            name=p.name,
            path=expanded,
            is_dir=is_dir,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
            is_hidden=p.name.startswith("."),
            is_symlink=p.is_symlink(),
            extension="" if is_dir else p.suffix.lower(),
        )

    async def exists(self, path: str) -> bool:
        return await aiofiles.os.path.exists(path)

    async def is_dir(self, path: str) -> bool:
        return await aiofiles.os.path.isdir(path)

    async def delete(self, path: str) -> None:
        p = Path(path)
        if p.is_dir():
            import shutil
            await aiofiles.os.wrap(shutil.rmtree)(path)
        else:
            await aiofiles.os.remove(path)

    async def rename(self, src: str, dst: str) -> None:
        await aiofiles.os.rename(src, dst)

    async def mkdir(self, path: str) -> None:
        await aiofiles.os.makedirs(path, exist_ok=True)

    async def trash(self, path: str) -> None:
        """Move a local path to XDG trash via send2trash."""
        import asyncio

        def _trash():
            try:
                import send2trash
                send2trash.send2trash(path)
            except ImportError:
                # Manual XDG trash fallback
                import shutil
                import time
                from pathlib import Path as P
                src = P(path)
                trash_dir = P.home() / ".local" / "share" / "Trash"
                files_dir = trash_dir / "files"
                info_dir = trash_dir / "info"
                files_dir.mkdir(parents=True, exist_ok=True)
                info_dir.mkdir(parents=True, exist_ok=True)
                dst = files_dir / src.name
                counter = 1
                while dst.exists():
                    dst = files_dir / f"{src.stem} ({counter}){src.suffix}"
                    counter += 1
                info_file = info_dir / f"{dst.name}.trashinfo"
                info_file.write_text(
                    f"[Trash Info]\n"
                    f"Path={src}\n"
                    f"DeletionDate={time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
                )
                shutil.move(str(src), str(dst))

        await asyncio.get_event_loop().run_in_executor(None, _trash)

    def get_parent(self, path: str) -> str:
        return str(Path(path).parent)

    def join(self, *parts: str) -> str:
        return str(Path(*parts))