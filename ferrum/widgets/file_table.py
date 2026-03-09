from datetime import datetime
from textual.widget import Widget
from textual.widgets import DataTable
from textual.app import ComposeResult
from textual import on
from textual.coordinate import Coordinate

from ferrum.backends.base import FileEntry
from ferrum.messages import DirectoryRequested, FileSelected


def format_size(size: int, is_dir: bool) -> str:
    if is_dir:
        return "<DIR>"
    for unit in ["B", "K", "M", "G", "T"]:
        if size < 1024:
            return f"{size:.0f}{unit}"
        size /= 1024
    return f"{size:.0f}P"


def format_date(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    return dt.strftime(fmt)


class FileTable(Widget):
    """The main file listing widget."""

    DEFAULT_CSS = """
    FileTable {
        height: 1fr;
        width: 1fr;
    }

    FileTable DataTable {
        height: 1fr;
        width: 1fr;
    }
    """

    def __init__(self, date_format: str = "%Y-%m-%d %H:%M") -> None:
        super().__init__()
        self.date_format = date_format
        self._entries: list[FileEntry] = []

    def compose(self) -> ComposeResult:
        table = DataTable(cursor_type="row")
        table.add_columns("Name", "Size", "Modified")
        yield table

    def populate(self, entries: list[FileEntry], show_hidden: bool = False) -> None:
        """Populate the table with file entries."""
        table = self.query_one(DataTable)
        table.clear()
        self._entries = []

        for entry in entries:
            if not show_hidden and entry.is_hidden:
                continue

            self._entries.append(entry)
            icon = "📁 " if entry.is_dir else "📄 "
            name = icon + entry.name
            if entry.is_symlink:
                name += " →"
            size = format_size(entry.size, entry.is_dir)
            modified = format_date(entry.modified, self.date_format)
            table.add_row(name, size, modified)

    def get_selected_entry(self) -> FileEntry | None:
        """Get the currently selected FileEntry."""
        table = self.query_one(DataTable)
        if table.cursor_row < len(self._entries):
            return self._entries[table.cursor_row]
        return None

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        entry = self.get_selected_entry()
        if entry is None:
            return
        if entry.is_dir:
            self.post_message(DirectoryRequested(entry.path))
        else:
            self.post_message(FileSelected(entry.path))