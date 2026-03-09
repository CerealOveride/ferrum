import tomllib
from pathlib import Path
from dataclasses import dataclass, field


CONFIG_DIR = Path.home() / ".config" / "ferrum"
USER_CONFIG = CONFIG_DIR / "config.toml"
DEFAULT_CONFIG = Path(__file__).parent.parent / "config" / "default.toml"


@dataclass
class GeneralConfig:
    show_hidden: bool = False
    confirm_delete: bool = True
    show_preview: bool = False
    sidebar_visible: bool = True


@dataclass
class AppearanceConfig:
    theme: str = "dark"
    show_icons: bool = True
    date_format: str = "%Y-%m-%d %H:%M"


@dataclass
class KeybindingsConfig:
    quit: str = "q"
    toggle_hidden: str = "ctrl+h"
    toggle_preview: str = "ctrl+p"
    toggle_sidebar: str = "ctrl+b"
    new_tab: str = "ctrl+t"
    close_tab: str = "ctrl+w"
    navigate_up: str = "backspace"
    delete: str = "delete"
    rename: str = "f2"
    copy: str = "ctrl+c"
    paste: str = "ctrl+v"
    cut: str = "ctrl+x"
    select_all: str = "ctrl+a"
    search: str = "ctrl+f"


@dataclass
class SMBConnection:
    name: str
    host: str
    share: str
    username: str = ""
    password: str = ""


@dataclass
class Config:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    appearance: AppearanceConfig = field(default_factory=AppearanceConfig)
    keybindings: KeybindingsConfig = field(default_factory=KeybindingsConfig)
    bookmarks: dict[str, str] = field(default_factory=dict)
    smb_connections: list[SMBConnection] = field(default_factory=list)


def load_config() -> Config:
    """Load config, merging defaults with user overrides."""
    config = Config()

    # Load defaults
    if DEFAULT_CONFIG.exists():
        with open(DEFAULT_CONFIG, "rb") as f:
            defaults = tomllib.load(f)
        _apply_config(config, defaults)

    # Load and merge user config if it exists
    if USER_CONFIG.exists():
        with open(USER_CONFIG, "rb") as f:
            user = tomllib.load(f)
        _apply_config(config, user)

    # Expand ~ in bookmarks
    config.bookmarks = {
        k: str(Path(v).expanduser())
        for k, v in config.bookmarks.items()
    }

    return config


def _apply_config(config: Config, data: dict) -> None:
    """Apply a config dict onto a Config object."""
    if "general" in data:
        for k, v in data["general"].items():
            if hasattr(config.general, k):
                setattr(config.general, k, v)

    if "appearance" in data:
        for k, v in data["appearance"].items():
            if hasattr(config.appearance, k):
                setattr(config.appearance, k, v)

    if "keybindings" in data:
        for k, v in data["keybindings"].items():
            if hasattr(config.keybindings, k):
                setattr(config.keybindings, k, v)

    if "bookmarks" in data:
        config.bookmarks.update(data["bookmarks"])

    if "smb" in data and "connections" in data["smb"]:
        for conn in data["smb"]["connections"]:
            config.smb_connections.append(SMBConnection(**conn))


def ensure_config_dir() -> None:
    """Create user config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_smb_connection(conn: SMBConnection) -> None:
    """Save an SMB connection to user config."""
    ensure_config_dir()

    # Load existing user config or start fresh
    if USER_CONFIG.exists():
        with open(USER_CONFIG, "rb") as f:
            import tomllib
            data = tomllib.load(f)
    else:
        data = {}

    # Ensure smb section exists
    if "smb" not in data:
        data["smb"] = {}
    if "connections" not in data["smb"]:
        data["smb"]["connections"] = []

    # Check if connection already exists and update, or append
    existing = data["smb"]["connections"]
    for i, c in enumerate(existing):
        if c.get("host") == conn.host and c.get("share") == conn.share:
            existing[i] = {
                "name": conn.name,
                "host": conn.host,
                "share": conn.share,
                "username": conn.username,
            }
            break
    else:
        existing.append({
            "name": conn.name,
            "host": conn.host,
            "share": conn.share,
            "username": conn.username,
        })

    _write_config(data)


def remove_smb_connection(host: str, share: str) -> None:
    """Remove an SMB connection from user config."""
    if not USER_CONFIG.exists():
        return

    with open(USER_CONFIG, "rb") as f:
        import tomllib
        data = tomllib.load(f)

    if "smb" in data and "connections" in data["smb"]:
        data["smb"]["connections"] = [
            c for c in data["smb"]["connections"]
            if not (c.get("host") == host and c.get("share") == share)
        ]

    _write_config(data)


def _write_config(data: dict) -> None:
    """Write config dict to user config file as TOML."""
    lines = []

    if "general" in data:
        lines.append("[general]")
        for k, v in data["general"].items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")

    if "appearance" in data:
        lines.append("[appearance]")
        for k, v in data["appearance"].items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")

    if "keybindings" in data:
        lines.append("[keybindings]")
        for k, v in data["keybindings"].items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")

    if "bookmarks" in data:
        lines.append("[bookmarks]")
        for k, v in data["bookmarks"].items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")

    if "smb" in data and "connections" in data["smb"]:
        for conn in data["smb"]["connections"]:
            lines.append("[[smb.connections]]")
            for k, v in conn.items():
                lines.append(f"{k} = {_toml_value(v)}")
            lines.append("")

    with open(USER_CONFIG, "w") as f:
        f.write("\n".join(lines))


def _toml_value(v) -> str:
    """Convert a Python value to a TOML value string."""
    if isinstance(v, bool):
        return "true" if v else "false"
    elif isinstance(v, str):
        return f'"{v}"'
    elif isinstance(v, int):
        return str(v)
    elif isinstance(v, float):
        return str(v)
    return f'"{v}"' 

def save_bookmark(name: str, path: str) -> None:
    """Save a bookmark to user config."""
    ensure_config_dir()

    if USER_CONFIG.exists():
        with open(USER_CONFIG, "rb") as f:
            import tomllib
            data = tomllib.load(f)
    else:
        data = {}

    if "bookmarks" not in data:
        data["bookmarks"] = {}

    data["bookmarks"][name] = path
    _write_config(data)


def remove_bookmark(name: str) -> None:
    """Remove a bookmark from user config."""
    if not USER_CONFIG.exists():
        return

    with open(USER_CONFIG, "rb") as f:
        import tomllib
        data = tomllib.load(f)

    if "bookmarks" in data and name in data["bookmarks"]:
        del data["bookmarks"][name]
        _write_config(data)
