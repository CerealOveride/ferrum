from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.containers import Horizontal
from textual.binding import Binding

from ferrum.config import load_config, ensure_config_dir
from ferrum.widgets.file_pane import FilePane


class FerrumApp(App):
    """Ferrum - A fast, stable TUI file manager."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #pane-container {
        layout: horizontal;
        height: 1fr;
    }
    """

    TITLE = "Ferrum"
    SUB_TITLE = "fe"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("backspace", "navigate_up", "Up"),
        Binding("ctrl+h", "toggle_hidden", "Hidden"),
    ]

    def __init__(self):
        super().__init__()
        ensure_config_dir()
        self.config = load_config()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="pane-container"):
            yield FilePane(str(Path.home()))
        yield Footer()

    def action_navigate_up(self) -> None:
        self.query_one(FilePane).navigate_up()

    def action_toggle_hidden(self) -> None:
        pane = self.query_one(FilePane)
        pane.show_hidden = not pane.show_hidden
        pane.load_directory(pane.current_path)