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