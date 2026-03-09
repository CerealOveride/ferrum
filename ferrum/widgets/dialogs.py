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


class InputDialog(ModalScreen):
    """Generic single input dialog."""

    DEFAULT_CSS = """
    InputDialog {
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

    #dialog-input {
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

    def __init__(self, title: str, placeholder: str = "", initial: str = "") -> None:
        super().__init__()
        self._title = title
        self._placeholder = placeholder
        self._initial = initial

    def compose(self) -> ComposeResult:
        from textual.widgets import Input
        with Vertical(id="dialog"):
            yield Label(self._title, id="dialog-title")
            yield Input(
                value=self._initial,
                placeholder=self._placeholder,
                id="dialog-input"
            )
            with Horizontal(id="dialog-buttons"):
                yield Button("Cancel", id="cancel", variant="default")
                yield Button("OK", id="ok", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#dialog-input").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            from textual.widgets import Input
            value = self.query_one("#dialog-input", Input).value.strip()
            self.dismiss(value if value else None)
        else:
            self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "enter":
            from textual.widgets import Input
            value = self.query_one("#dialog-input", Input).value.strip()
            self.dismiss(value if value else None)
        elif event.key == "escape":
            self.dismiss(None)
