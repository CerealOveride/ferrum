from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.containers import Horizontal
from textual.binding import Binding

from ferrum.config import load_config, ensure_config_dir
from ferrum.widgets.file_pane import FilePane
from ferrum.widgets.sidebar import Sidebar
from ferrum.widgets.preview import PreviewPane
from ferrum.messages import DirectoryRequested, FileSelected


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
        Binding("ctrl+b", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+t", "new_tab", "New Tab"),
        Binding("ctrl+w", "close_tab", "Close Tab"),
        Binding("ctrl+e", "toggle_preview", "Preview"),
    ]

    def __init__(self):
        super().__init__()
        ensure_config_dir()
        self.config = load_config()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="pane-container"):
            yield Sidebar(
                bookmarks=self.config.bookmarks,
                smb_connections=self.config.smb_connections,
            )
            yield FilePane(str(Path.home()))
            yield PreviewPane()
        yield Footer()

    def on_directory_requested(self, event: DirectoryRequested) -> None:
        self.query_one(FilePane).load_directory(event.path)

    def on_file_selected(self, event: FileSelected) -> None:
        preview = self.query_one(PreviewPane)
        preview.preview(event.path)
        self.notify(f"Preview: {event.path}")

    def action_navigate_up(self) -> None:
        self.query_one(FilePane).navigate_up()

    def action_toggle_hidden(self) -> None:
        pane = self.query_one(FilePane)
        active = pane.get_active_pane()
        if active:
            active.show_hidden = not active.show_hidden
            active.load_directory(active.current_path)

    def action_toggle_sidebar(self) -> None:
        self.query_one(Sidebar).toggle()

    def action_new_tab(self) -> None:
        self.query_one(FilePane).new_tab()

    def action_close_tab(self) -> None:
        self.query_one(FilePane).close_tab()

    def action_toggle_preview(self) -> None:
        self.query_one(PreviewPane).toggle()