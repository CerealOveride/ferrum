from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import ProgressBar, Label
from textual.containers import Horizontal
from textual.reactive import reactive

from ferrum.operations.types import FileOperation


class FerrumFooter(Widget):
    """Custom footer with keybindings and operation progress."""

    DEFAULT_CSS = """
    FerrumFooter {
        height: 4;
        layout: vertical;
        background: $panel;
    }

    #keybindings {
        height: 1;
        background: $panel;
        padding: 0 1;
        color: $text-muted;
    }

    #selection-status {
        height: 1;
        background: $panel;
        padding: 0 1;
        color: $accent;
        display: none;
    }
    #selection-status.active {
        display: block;
    }
    #progress-bar-row {
        height: 2;
        layout: horizontal;
        background: $panel;
        padding: 0 1;
        display: none;
    }

    #progress-bar-row.active {
        display: block;
    }

    #progress-label {
        width: 1fr;
        height: 1;
        color: $text;
    }

    #progress-bar {
        width: 30;
        height: 1;
    }

    #progress-file {
        width: 1fr;
        height: 1;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("", id="keybindings")
        yield Label("", id="selection-status")
        with Horizontal(id="progress-bar-row"):
            yield Label("", id="progress-label")
            yield ProgressBar(total=100, show_eta=False, id="progress-bar")
            yield Label("", id="progress-file")

    def on_mount(self) -> None:
        self._update_keybindings()

    def _update_keybindings(self) -> None:
        bindings = [
            ("q", "Quit"),
            ("⌫", "Up"),
            ("^h", "Hidden"),
            ("^b", "Sidebar"),
            ("^t", "New Tab"),
            ("^w", "Close Tab"),
            ("^e", "Preview"),
            ("^c", "Copy"),
            ("^x", "Cut"),
            ("^v", "Paste"),
            ("Del", "Trash"),
            ("F2", "Rename"),
        ]
        text = "  ".join(f"[bold cyan]{k}[/bold cyan] {v}" for k, v in bindings)
        self.query_one("#keybindings", Label).update(text)

    def update_selection(self, count: int, total: int) -> None:
        """Show or hide selection count in footer."""
        label = self.query_one("#selection-status", Label)
        if count > 0:
            label.update(f"[bold]{count}[/bold] of {total} selected")
            label.add_class("active")
            label.styles.display = "block"
        else:
            label.remove_class("active")
            label.styles.display = "none"

    def show_progress(self, op: FileOperation) -> None:
        """Show operation progress in the footer."""
        row = self.query_one("#progress-bar-row")
        row.add_class("active")
        row.styles.display = "block"

        label = self.query_one("#progress-label", Label)
        bar = self.query_one("#progress-bar", ProgressBar)
        file_label = self.query_one("#progress-file", Label)

        label.update(f"{op.description} ({op.completed_files}/{op.total_files})")
        bar.progress = int(op.progress * 100)
        file_label.update(op.current_file)

    def hide_progress(self) -> None:
        """Hide the progress bar."""
        row = self.query_one("#progress-bar-row")
        row.remove_class("active")
        row.styles.display = "none"