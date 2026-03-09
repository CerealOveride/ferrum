from datetime import datetime
from textual.widget import Widget
from textual.widgets import DataTable
from textual.app import ComposeResult
from textual import on
from textual.events import Click

from ferrum.backends.base import FileEntry
from ferrum.messages import DirectoryRequested, FileSelected, FileOpened


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
    """The main file listing widget with multi-selection support."""

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
        self._selected: set[int] = set()
        self._last_click_row: int | None = None

    def compose(self) -> ComposeResult:
        table = DataTable(cursor_type="row")
        table.add_columns("Name", "Size", "Modified")
        yield table

    def populate(self, entries: list[FileEntry], show_hidden: bool = False) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self._entries = []
        self._selected = set()
        for entry in entries:
            if not show_hidden and entry.is_hidden:
                continue
            self._entries.append(entry)
            self._add_row(len(self._entries) - 1)

    def _add_row(self, idx: int) -> None:
        table = self.query_one(DataTable)
        entry = self._entries[idx]
        icon = "📁 " if entry.is_dir else "📄 "
        mark = "● " if idx in self._selected else "  "
        name = mark + icon + entry.name
        if entry.is_symlink:
            name += " →"
        size = format_size(entry.size, entry.is_dir)
        modified = format_date(entry.modified, self.date_format)
        table.add_row(name, size, modified)

    def _refresh_rows(self) -> None:
        table = self.query_one(DataTable)
        current_row = table.cursor_row
        table.clear()
        for i in range(len(self._entries)):
            self._add_row(i)
        if current_row < len(self._entries):
            table.move_cursor(row=current_row)

    def get_selected_entry(self) -> FileEntry | None:
        table = self.query_one(DataTable)
        if table.cursor_row < len(self._entries):
            return self._entries[table.cursor_row]
        return None

    def get_selected_paths(self) -> list[str]:
        return [self._entries[i].path for i in sorted(self._selected)]

    def toggle_selection(self, row: int) -> None:
        if row in self._selected:
            self._selected.discard(row)
        else:
            self._selected.add(row)
        self._refresh_rows()

    def range_select(self, from_row: int, to_row: int) -> None:
        start = min(from_row, to_row)
        end = max(from_row, to_row)
        for i in range(start, end + 1):
            self._selected.add(i)
        self._refresh_rows()

    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        entry = self.get_selected_entry()
        if entry:
            self.post_message(FileSelected(entry.path))

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        entry = self.get_selected_entry()
        if entry is None:
            return
        if entry.is_dir:
            self.post_message(DirectoryRequested(entry.path))
        else:
            self.post_message(FileSelected(entry.path))

    def on_key(self, event) -> None:
        if event.key == "space":
            table = self.query_one(DataTable)
            self.toggle_selection(table.cursor_row)
            event.stop()

    def on_click(self, event: Click) -> None:
        table = self.query_one(DataTable)
        current_row = table.cursor_row
        if event.shift and self._last_click_row is not None:
            self.range_select(self._last_click_row, current_row)
        self._last_click_row = current_row
