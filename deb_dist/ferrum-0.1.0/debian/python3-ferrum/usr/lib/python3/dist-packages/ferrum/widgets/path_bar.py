from textual.widget import Widget
from textual.widgets import Input
from textual.app import ComposeResult
from textual import on

from ferrum.messages import DirectoryRequested


class PathBar(Widget):
    """Displays and allows editing of the current path."""

    DEFAULT_CSS = """
    PathBar {
        height: 3;
        border: solid $primary;
        padding: 0 1;
    }

    PathBar Input {
        border: none;
        height: 1;
        background: transparent;
        width: 1fr;
        color: $text;
    }

    PathBar Input:focus {
        background: $surface;
        color: $text;
        border: none;
    }

    PathBar Input>.input--cursor {
        color: $text;
        background: $accent;
    }

    PathBar Input>.input--placeholder {
        color: $text-muted;
    }
    """

    def __init__(self, initial_path: str = "~") -> None:
        super().__init__()
        self.current_path = initial_path

    def compose(self) -> ComposeResult:
        yield Input(value=self.current_path, placeholder="Enter path...")

    def update_path(self, path: str) -> None:
        """Update the displayed path."""
        self.current_path = path
        self.query_one(Input).value = path

    @on(Input.Submitted)
    def on_path_submitted(self, event: Input.Submitted) -> None:
        """Navigate to the entered path."""
        self.post_message(DirectoryRequested(event.value))