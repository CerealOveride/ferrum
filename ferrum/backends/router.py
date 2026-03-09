import keyring
from ferrum.backends.base import FSBackend
from ferrum.backends.local import LocalBackend

KEYRING_SERVICE = "ferrum-smb"


def is_smb_path(path: str) -> bool:
    """Check if a path is an SMB path."""
    return path.startswith("//") or path.startswith("\\\\")


def _decode_keyring_key(key: str) -> str:
    """Decode keyrings.alt encoded key back to original string."""
    # keyrings.alt replaces special chars with _XX hex codes
    import re
    def replace(m):
        return chr(int(m.group(1), 16))
    return re.sub(r'_([0-9a-fA-F]{2})', replace, key)


def _find_username_for_host(host: str) -> str | None:
    """Find a stored username for a given host by reading keyring file."""
    try:
        import configparser
        from pathlib import Path

        keyring_file = Path.home() / ".local" / "share" / "python_keyring" / "keyring_pass.cfg"
        if not keyring_file.exists():
            return None

        config = configparser.ConfigParser()
        config.read(keyring_file)

        # Find the encoded service name
        for section in config.sections():
            decoded_section = _decode_keyring_key(section)
            if decoded_section != KEYRING_SERVICE:
                continue
            # Found our service section — look for a key matching @host
            for encoded_key in config[section]:
                decoded_key = _decode_keyring_key(encoded_key)
                if decoded_key.endswith(f"@{host}"):
                    username = decoded_key.split(f"@{host}")[0]
                    return username
    except Exception:
        pass
    return None


# Global config connections cache — set by app on startup
_config_connections: list = []


def set_config_connections(connections: list) -> None:
    """Cache SMB connections from config for use by router."""
    global _config_connections
    _config_connections = connections


def get_backend_for_path(path: str, smb_connections: dict = None) -> FSBackend:
    """Return the appropriate backend for a given path."""
    if is_smb_path(path):
        from ferrum.backends.smb import SMBBackend, SMBConnection, parse_smb_url
        host, share, _ = parse_smb_url(path)

        # Look for a matching configured connection first
        if smb_connections:
            for conn in smb_connections.values():
                if conn.host == host and conn.share == share:
                    return SMBBackend(conn)

        # Check global config connections
        for conn in _config_connections:
            if conn.host == host and conn.share == share:
                # Build SMBConnection with keyring lookup
                password = keyring.get_password(
                    KEYRING_SERVICE, f"{conn.username}@{host}"
                ) if conn.username else None
                smb_conn = SMBConnection(
                    name=conn.name,
                    host=host,
                    share=share,
                    username=conn.username,
                    password=password or "",
                    use_keyring=True,
                )
                return SMBBackend(smb_conn)

        # Fall back to keyring username discovery
        username = _find_username_for_host(host)
        password = None
        if username:
            password = keyring.get_password(KEYRING_SERVICE, f"{username}@{host}")

        connection = SMBConnection(
            name=f"{host}/{share}",
            host=host,
            share=share,
            username=username or "",
            password=password or "",
            use_keyring=True,
        )
        return SMBBackend(connection)

    return LocalBackend()
