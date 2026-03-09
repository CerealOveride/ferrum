from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Label
from textual.containers import Vertical, Horizontal

from ferrum.operations.types import ConflictResolution


class ConflictDialog(ModalScreen):
    """Dialog shown when a file conflict is detected."""

    DEFAULT_CSS = """
    ConflictDialog {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }

    #dialog-title {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #dialog-message {
        color: $text-muted;
        margin-bottom: 1;
    }

    #dialog-buttons {
        layout: horizontal;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("File Conflict", id="dialog-title")
            yield Label(
                f"'{self.filename}' already exists at the destination.",
                id="dialog-message"
            )
            with Horizontal(id="dialog-buttons"):
                yield Button("Skip", id="skip", variant="default")
                yield Button("Overwrite", id="overwrite", variant="warning")
                yield Button("Rename", id="rename", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "skip":
                self.dismiss(ConflictResolution.SKIP)
            case "overwrite":
                self.dismiss(ConflictResolution.OVERWRITE)
            case "rename":
                self.dismiss(ConflictResolution.RENAME)


class ConfirmDialog(ModalScreen):
    """Generic confirmation dialog."""

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: auto;
        border: solid $error;
        background: $surface;
        padding: 1 2;
    }

    #dialog-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    #dialog-message {
        color: $text-muted;
        margin-bottom: 1;
    }

    #dialog-buttons {
        layout: horizontal;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title, id="dialog-title")
            yield Label(self._message, id="dialog-message")
            with Horizontal(id="dialog-buttons"):
                yield Button("Cancel", id="cancel", variant="default")
                yield Button("Delete", id="confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")
