from pathlib import Path
from textual.widget import Widget
from textual.app import ComposeResult
from textual.containers import Vertical
from textual import on, work

from ferrum.backends.local import LocalBackend
from ferrum.widgets.file_table import FileTable
from ferrum.widgets.path_bar import PathBar
from ferrum.messages import DirectoryRequested, DirectoryLoaded, DirectoryError


class FilePane(Widget):
    """A single file browsing pane with path bar and file table."""

    DEFAULT_CSS = """
    FilePane {
        height: 1fr;
        width: 1fr;
        border: solid $panel;
    }
    """

    def __init__(self, initial_path: str = "~") -> None:
        super().__init__()
        self.current_path = str(Path(initial_path).expanduser().resolve())
        self.backend = LocalBackend()
        self.show_hidden = False
        self._history: list[str] = []

    def compose(self) -> ComposeResult:
        yield PathBar(self.current_path)
        yield FileTable()

    def on_mount(self) -> None:
        self.load_directory(self.current_path)

    @work(exclusive=True)
    async def load_directory(self, path: str) -> None:
        """Load a directory in the background."""
        try:
            entries = await self.backend.list_dir(path)
            self.current_path = path
            self.post_message(DirectoryLoaded(path, entries))
        except (PermissionError, FileNotFoundError) as e:
            self.post_message(DirectoryError(path, str(e)))

    @on(DirectoryRequested)
    def on_directory_requested(self, event: DirectoryRequested) -> None:
        event.stop()
        self._history.append(self.current_path)
        self.load_directory(event.path)

    @on(DirectoryLoaded)
    def on_directory_loaded(self, event: DirectoryLoaded) -> None:
        event.stop()
        self.query_one(PathBar).update_path(event.path)
        self.query_one(FileTable).populate(event.entries, self.show_hidden)

    @on(DirectoryError)
    def on_directory_error(self, event: DirectoryError) -> None:
        event.stop()
        self.app.notify(f"Error: {event.error}", severity="error")

    def navigate_up(self) -> None:
        """Navigate to parent directory."""
        parent = self.backend.get_parent(self.current_path)
        if parent != self.current_path:
            self._history.append(self.current_path)
            self.load_directory(parent)

    def navigate_back(self) -> None:
        """Navigate back in history."""
        if self._history:
            path = self._history.pop()
            self.load_directory(path)