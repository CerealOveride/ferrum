import asyncio
import keyring
from keyrings.alt.file import PlaintextKeyring
keyring.set_keyring(PlaintextKeyring())
from datetime import datetime
from pathlib import PurePosixPath
from typing import Optional

import smbclient
import smbclient.shutil
from smbprotocol.exceptions import SMBException, SMBConnectionClosed, SMBAuthenticationError

from ferrum.backends.base import FSBackend, FileEntry


KEYRING_SERVICE = "ferrum-smb"


def smb_path(host: str, share: str, path: str = "") -> str:
    """Build a UNC path for smbclient."""
    base = f"\\\\{host}\\{share}"
    if path:
        # Convert forward slashes to backslashes for smbclient
        path = path.replace("/", "\\").lstrip("\\")
        return f"{base}\\{path}"
    return base


def parse_smb_url(url: str) -> tuple[str, str, str]:
    """Parse //host/share/path into (host, share, path).
    
    Returns (host, share, remaining_path)
    """
    # Strip leading slashes
    url = url.lstrip("/")
    parts = url.split("/", 2)
    host = parts[0] if len(parts) > 0 else ""
    share = parts[1] if len(parts) > 1 else ""
    path = parts[2] if len(parts) > 2 else ""
    return host, share, path


def store_credentials(host: str, username: str, password: str) -> None:
    """Store SMB credentials in system keyring."""
    keyring.set_password(KEYRING_SERVICE, f"{username}@{host}", password)


def get_credentials(host: str, username: str) -> Optional[str]:
    """Retrieve SMB credentials from system keyring."""
    return keyring.get_password(KEYRING_SERVICE, f"{username}@{host}")


def delete_credentials(host: str, username: str) -> None:
    """Remove SMB credentials from system keyring."""
    try:
        keyring.delete_password(KEYRING_SERVICE, f"{username}@{host}")
    except keyring.errors.PasswordDeleteError:
        pass


class SMBConnection:
    """Represents a configured SMB connection."""

    def __init__(
        self,
        name: str,
        host: str,
        share: str,
        username: str = "",
        password: str = "",
        use_keyring: bool = True,
    ):
        self.name = name
        self.host = host
        self.share = share
        self.username = username
        self._password = password
        self.use_keyring = use_keyring
        self._connected = False

    @property
    def password(self) -> str:
        if self.use_keyring and self.username:
            stored = get_credentials(self.host, self.username)
            if stored:
                return stored
        return self._password

    def connect(self) -> None:
        """Register connection with smbclient."""
        try:
            kwargs = {
                "username": self.username or None,
                "password": self.password or None,
            }
            # Remove None values for guest connections
            kwargs = {k: v for k, v in kwargs.items() if v is not None}
            smbclient.register_session(self.host, **kwargs)
            self._connected = True
        except SMBAuthenticationError as e:
            raise PermissionError(f"SMB auth failed for {self.host}: {e}")
        except SMBException as e:
            # When a guest session is established but the server requires signing/encryption,
            # smbprotocol raises a plain SMBException (not SMBAuthenticationError).
            # Treat this as an auth failure so the credential dialog is shown.
            if "guest" in str(e).lower() and ("signing" in str(e).lower() or "encryption" in str(e).lower()):
                raise PermissionError(f"SMB auth failed for {self.host}: {e}")
            raise ConnectionError(f"SMB connection failed for {self.host}: {e}")

    def disconnect(self) -> None:
        """Close the SMB session."""
        try:
            smbclient.delete_session(self.host)
        except Exception:
            pass
        self._connected = False

    def ensure_connected(self) -> None:
        """Connect if not already connected."""
        if not self._connected:
            self.connect()


class SMBBackend(FSBackend):
    """Backend for SMB/CIFS network share access."""

    def __init__(self, connection: SMBConnection):
        self.connection = connection

    def _unc(self, path: str) -> str:
        """Convert a path to a UNC path for smbclient."""
        _, _, remaining = parse_smb_url(path)
        return smb_path(self.connection.host, self.connection.share, remaining)

    def _ensure(self) -> None:
        """Ensure we have an active SMB connection."""
        self.connection.ensure_connected()

    async def list_dir(self, path: str) -> list[FileEntry]:
        """List SMB directory contents."""
        def _list():
            self._ensure()
            entries = []
            unc = self._unc(path)
            try:
                for entry in smbclient.scandir(unc):
                    try:
                        stat = entry.stat()
                        is_dir = entry.is_dir()
                        name = entry.name
                        # Reconstruct the smb:// style path
                        entry_path = f"//{self.connection.host}/{self.connection.share}"
                        _, _, remaining = parse_smb_url(path)
                        if remaining:
                            entry_path += f"/{remaining}/{name}"
                        else:
                            entry_path += f"/{name}"

                        entries.append(FileEntry(
                            name=name,
                            path=entry_path,
                            is_dir=is_dir,
                            size=stat.st_size,
                            modified=datetime.fromtimestamp(stat.st_mtime),
                            is_hidden=name.startswith("."),
                            is_symlink=False,
                            extension="" if is_dir else PurePosixPath(name).suffix.lower(),
                        ))
                    except (SMBException, OSError):
                        continue

                entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
                return entries

            except SMBConnectionClosed:
                self.connection._connected = False
                raise ConnectionError(f"SMB connection lost to {self.connection.host}")
            except SMBException as e:
                raise OSError(f"SMB error listing {path}: {e}")

        return await asyncio.get_event_loop().run_in_executor(None, _list)

    async def stat(self, path: str) -> FileEntry:
        def _stat():
            self._ensure()
            unc = self._unc(path)
            s = smbclient.stat(unc)
            name = PurePosixPath(path).name
            is_dir = smbclient.path.isdir(unc)
            return FileEntry(
                name=name,
                path=path,
                is_dir=is_dir,
                size=s.st_size,
                modified=datetime.fromtimestamp(s.st_mtime),
                is_hidden=name.startswith("."),
                is_symlink=False,
                extension="" if is_dir else PurePosixPath(name).suffix.lower(),
            )
        return await asyncio.get_event_loop().run_in_executor(None, _stat)

    async def exists(self, path: str) -> bool:
        def _exists():
            self._ensure()
            return smbclient.path.exists(self._unc(path))
        return await asyncio.get_event_loop().run_in_executor(None, _exists)

    async def is_dir(self, path: str) -> bool:
        def _isdir():
            self._ensure()
            return smbclient.path.isdir(self._unc(path))
        return await asyncio.get_event_loop().run_in_executor(None, _isdir)

    async def delete(self, path: str) -> None:
        def _delete():
            self._ensure()
            unc = self._unc(path)
            if smbclient.path.isdir(unc):
                smbclient.shutil.rmtree(unc)
            else:
                smbclient.remove(unc)
        await asyncio.get_event_loop().run_in_executor(None, _delete)

    async def rename(self, src: str, dst: str) -> None:
        def _rename():
            self._ensure()
            smbclient.rename(self._unc(src), self._unc(dst))
        await asyncio.get_event_loop().run_in_executor(None, _rename)

    async def mkdir(self, path: str) -> None:
        def _mkdir():
            self._ensure()
            smbclient.makedirs(self._unc(path), exist_ok=True)
        await asyncio.get_event_loop().run_in_executor(None, _mkdir)

    def get_parent(self, path: str) -> str:
        """Get parent of an SMB path."""
        p = PurePosixPath(path)
        parent = str(p.parent)
        # Don't go above //host/share
        _, _, remaining = parse_smb_url(path)
        if not remaining:
            return path  # already at share root
        return parent

    def join(self, *parts: str) -> str:
        return str(PurePosixPath(*parts))
