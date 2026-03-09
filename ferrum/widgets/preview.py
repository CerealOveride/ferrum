import os
from pathlib import Path
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Vertical
from textual import work
from rich.syntax import Syntax
from rich.text import Text
from rich.panel import Panel


# File extensions we'll attempt to preview as text
TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json",
    ".toml", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".sh", ".bash",
    ".zsh", ".fish", ".rs", ".go", ".c", ".cpp", ".h", ".java", ".rb",
    ".php", ".xml", ".csv", ".log", ".env", ".gitignore", ".dockerfile",
    ".nix", ".vim", ".lua",
}

# File extensions we'll attempt to preview as images
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg",
}

# How many lines of text to preview
PREVIEW_LINES = 50
# Max file size for text preview (1MB)
MAX_TEXT_SIZE = 1024 * 1024


def detect_language(path: str) -> str:
    """Detect language for syntax highlighting."""
    ext = Path(path).suffix.lower()
    mapping = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".html": "html", ".css": "css", ".json": "json", ".toml": "toml",
        ".yaml": "yaml", ".yml": "yaml", ".sh": "bash", ".bash": "bash",
        ".zsh": "bash", ".rs": "rust", ".go": "go", ".c": "c",
        ".cpp": "cpp", ".h": "c", ".java": "java", ".rb": "ruby",
        ".php": "php", ".xml": "xml", ".nix": "nix", ".lua": "lua",
        ".md": "markdown", ".vim": "vim",
    }
    return mapping.get(ext, "text")


class PreviewPane(Widget):
    """Toggleable preview pane for files and directories."""

    DEFAULT_CSS = """
    PreviewPane {
        width: 40;
        height: 1fr;
        border-left: solid $panel;
        background: $surface;
        display: none;
    }

    PreviewPane.visible {
        display: block;
    }

    PreviewPane #preview-content {
        height: 1fr;
        padding: 1;
        overflow-y: auto;
    }

    PreviewPane #preview-title {
        height: 3;
        padding: 0 1;
        border-bottom: solid $panel;
        content-align: center middle;
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_path: str | None = None
        self._visible = False

    def compose(self) -> ComposeResult:
        yield Static("", id="preview-title")
        yield Static("", id="preview-content")

    def toggle(self) -> None:
        """Show or hide the preview pane."""
        self._visible = not self._visible
        if self._visible:
            self.add_class("visible")
            if self._current_path:
                self.preview(self._current_path)
        else:
            self.remove_class("visible")

    def preview(self, path: str) -> None:
        """Preview a file or directory."""
        self._current_path = path
        if not self._visible:
            return
        self._load_preview(path)

    @work(exclusive=True)
    async def _load_preview(self, path: str) -> None:
        """Load preview content in the background."""
        p = Path(path)
        title = self.query_one("#preview-title", Static)
        content = self.query_one("#preview-content", Static)

        title.update(p.name or path)

        if not p.exists():
            content.update("[red]Path does not exist[/red]")
            return

        if p.is_dir():
            await self._preview_directory(p, content)
        elif p.suffix.lower() in IMAGE_EXTENSIONS:
            await self._preview_image(p, content)
        elif p.suffix.lower() in TEXT_EXTENSIONS:
            await self._preview_text(p, content)
        else:
            await self._preview_metadata(p, content)

    async def _preview_directory(self, p: Path, content: Static) -> None:
        """Preview directory contents."""
        try:
            items = list(p.iterdir())
            dirs = [i for i in items if i.is_dir()]
            files = [i for i in items if i.is_file()]
            text = Text()
            text.append("📁 Directory\n\n", style="bold yellow")
            text.append(f"Items:  {len(items)}\n", style="cyan")
            text.append(f"Dirs:   {len(dirs)}\n", style="cyan")
            text.append(f"Files:  {len(files)}\n\n", style="cyan")
            try:
                stat = p.stat()
                import datetime
                modified = datetime.datetime.fromtimestamp(stat.st_mtime)
                text.append(f"Modified:\n{modified.strftime('%Y-%m-%d %H:%M')}\n", style="dim")
            except OSError:
                pass
            content.update(text)
        except PermissionError:
            content.update("[red]Permission denied[/red]")

    async def _preview_text(self, p: Path, content: Static) -> None:
        """Preview text file with syntax highlighting."""
        try:
            size = p.stat().st_size
            if size > MAX_TEXT_SIZE:
                content.update(f"[yellow]File too large to preview\n({size // 1024}KB)[/yellow]")
                return

            with open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= PREVIEW_LINES:
                        break
                    lines.append(line)

            code = "".join(lines)
            language = detect_language(str(p))

            syntax = Syntax(
                code,
                language,
                theme="monokai",
                line_numbers=True,
                word_wrap=False,
            )
            content.update(syntax)

        except (OSError, UnicodeDecodeError) as e:
            content.update(f"[red]Cannot read file:\n{e}[/red]")

    async def _preview_image(self, p: Path, content: Static) -> None:
        """Preview image using Kitty graphics protocol if available."""
        term = os.environ.get("TERM", "")
        colorterm = os.environ.get("COLORTERM", "")

        # Check if we're in Kitty
        if "kitty" in term.lower():
            try:
                # Use kitty icat for image display
                # We render metadata + a note that image is displayed
                stat = p.stat()
                size_kb = stat.st_size // 1024
                text = Text()
                text.append("🖼 Image\n\n", style="bold cyan")
                text.append(f"Size: {size_kb}KB\n", style="dim")
                text.append(f"Type: {p.suffix.upper()[1:]}\n\n", style="dim")
                text.append(
                    "Image preview available\nvia kitty icat.\n\n"
                    "Full image viewer\ncoming soon.",
                    style="italic dim"
                )
                content.update(text)
            except OSError as e:
                content.update(f"[red]Cannot read image:\n{e}[/red]")
        else:
            await self._preview_metadata(p, content)

    async def _preview_metadata(self, p: Path, content: Static) -> None:
        """Show file metadata for unknown file types."""
        try:
            stat = p.stat()
            import datetime
            size = stat.st_size
            modified = datetime.datetime.fromtimestamp(stat.st_mtime)

            # Format size nicely
            for unit in ["B", "KB", "MB", "GB"]:
                if size < 1024:
                    size_str = f"{size:.1f} {unit}"
                    break
                size /= 1024
            else:
                size_str = f"{size:.1f} TB"

            text = Text()
            text.append("📄 File\n\n", style="bold")
            text.append(f"Size:\n  {size_str}\n\n", style="cyan")
            text.append(f"Modified:\n  {modified.strftime('%Y-%m-%d %H:%M')}\n\n", style="cyan")
            text.append(f"Extension:\n  {p.suffix or 'none'}\n", style="dim")
            content.update(text)

        except OSError as e:
            content.update(f"[red]Cannot stat file:\n{e}[/red]")