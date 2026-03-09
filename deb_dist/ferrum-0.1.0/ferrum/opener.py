import asyncio
import subprocess
import tempfile
import os
from pathlib import Path

from ferrum.backends.router import is_smb_path


async def open_file(path: str) -> None:
    """Open a file with xdg-open, handling SMB paths via temp file."""
    if is_smb_path(path):
        await _open_smb_file(path)
    else:
        await _open_local_file(path)


async def _open_local_file(path: str) -> None:
    """Open a local file with xdg-open."""
    await asyncio.create_subprocess_exec(
        "xdg-open", path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )


async def _open_smb_file(path: str) -> None:
    """Download SMB file to temp location and open with xdg-open."""
    import smbclient
    from ferrum.backends.smb import parse_smb_url, smb_path
    from ferrum.backends.router import _find_username_for_host, KEYRING_SERVICE
    import keyring

    def _download():
        host, share, remaining = parse_smb_url(path)
        unc = smb_path(host, share, remaining)

        username = _find_username_for_host(host)
        password = None
        if username:
            password = keyring.get_password(KEYRING_SERVICE, f"{username}@{host}")
        try:
            kwargs = {}
            if username:
                kwargs["username"] = username
            if password:
                kwargs["password"] = password
            smbclient.register_session(host, **kwargs)
        except Exception:
            pass

        # Create temp file with same extension
        suffix = Path(path).suffix
        tmp = tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
            prefix="ferrum_"
        )
        with smbclient.open_file(unc, mode="rb") as src:
            tmp.write(src.read())
        tmp.close()
        return tmp.name

    loop = asyncio.get_event_loop()
    tmp_path = await loop.run_in_executor(None, _download)

    # Open the temp file
    await asyncio.create_subprocess_exec(
        "xdg-open", tmp_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    # Schedule cleanup after a delay to give the app time to open the file
    asyncio.create_task(_cleanup_later(tmp_path, delay=30))


async def _cleanup_later(path: str, delay: int = 30) -> None:
    """Delete a temp file after a delay."""
    await asyncio.sleep(delay)
    try:
        os.unlink(path)
    except OSError:
        pass
