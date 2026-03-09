from datetime import datetime
from textual.widget import Widget
from textual.widgets import DataTable, Input
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
        self._sort_column: str = "Name"
        self._sort_reverse: bool = False
        self._all_entries: list = []  # unfiltered, unsorted master list
        self._last_click_row: int | None = None
        self._search_query: str = ""
        self._search_visible: bool = False

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search...", id="search-bar")
        table = DataTable(cursor_type="row")
        table.add_columns("Name", "Size", "Modified")
        yield table

    def populate(self, entries: list[FileEntry], show_hidden: bool = False) -> None:
        self._all_entries = entries
        self._show_hidden = show_hidden
        self._apply_sort()

    def _apply_sort(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        # Rebuild columns with sort indicator on active column
        for name in ("Name", "Size", "Modified"):
            if name == self._sort_column:
                table.add_column(f"{name} {'▼' if self._sort_reverse else '▲'}", key=name)
            else:
                table.add_column(name, key=name)
        self._entries = []
        self._selected = set()
        try:
            from ferrum.widgets.footer import FerrumFooter
            footer = self.app.query_one(FerrumFooter)
            footer.update_selection(0, 0)
        except Exception:
            pass

        show_hidden = getattr(self, "_show_hidden", False)
        query = getattr(self, "_search_query", "")
        visible = [e for e in self._all_entries if show_hidden or not e.is_hidden]
        if query:
            visible = [e for e in visible if query in e.name.lower()]

        # Always sort dirs first, then apply column sort
        col = self._sort_column
        rev = self._sort_reverse
        if col == "Name":
            key_fn = lambda e: (not e.is_dir, e.name.lower())
        elif col == "Size":
            key_fn = lambda e: (not e.is_dir, e.size or 0)
        elif col == "Modified":
            key_fn = lambda e: (not e.is_dir, e.modified or 0)
        else:
            key_fn = lambda e: (not e.is_dir, e.name.lower())

        # Reverse only the within-group sort, not the dirs-first ordering
        dirs = sorted([e for e in visible if e.is_dir], key=lambda e: e.name.lower() if col == "Name" else (e.size or 0) if col == "Size" else (e.modified or 0), reverse=rev)
        files = sorted([e for e in visible if not e.is_dir], key=lambda e: e.name.lower() if col == "Name" else (e.size or 0) if col == "Size" else (e.modified or 0), reverse=rev)
        sorted_entries = dirs + files

        for entry in sorted_entries:
            self._entries.append(entry)
            self._add_row(len(self._entries) - 1)

    @on(DataTable.HeaderSelected)
    def on_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Sort by clicked column header."""
        # Strip any existing sort indicator to get the base column name
        col_label = str(event.label).strip().rstrip("▲▼").strip()
        if self._sort_column == col_label:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col_label
            self._sort_reverse = False
        self._apply_sort()
        # Update column headers to show sort indicator
        table = self.query_one(DataTable)
        for col in table.columns.values():
            label = str(col.label).strip().rstrip("▲▼").strip()
            if label == col_label:
                col.label = f"{label} {'▼' if self._sort_reverse else '▲'}"
            else:
                col.label = label

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
        self._notify_selection()

    def range_select(self, from_row: int, to_row: int) -> None:
        start = min(from_row, to_row)
        end = max(from_row, to_row)
        for i in range(start, end + 1):
            self._selected.add(i)
        self._refresh_rows()
        self._notify_selection()

    def show_search(self) -> None:
        """Show the search bar and focus it."""
        bar = self.query_one("#search-bar", Input)
        self._search_visible = True
        bar.add_class("visible")
        bar.styles.display = "block"
        bar.focus()

    def hide_search(self) -> None:
        """Hide the search bar and clear the filter."""
        bar = self.query_one("#search-bar", Input)
        bar.value = ""
        self._search_query = ""
        self._search_visible = False
        bar.remove_class("visible")
        bar.styles.display = "none"
        self._apply_sort()
        self.query_one(DataTable).focus()

    @on(Input.Changed, "#search-bar")
    def on_search_changed(self, event: Input.Changed) -> None:
        self._search_query = event.value.lower()
        self._apply_sort()

    @on(Input.Submitted, "#search-bar")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        """Enter in search bar moves focus to table."""
        self.query_one(DataTable).focus()

    def _notify_selection(self) -> None:
        """Update footer with current selection count."""
        try:
            from ferrum.widgets.footer import FerrumFooter
            footer = self.app.query_one(FerrumFooter)
            footer.update_selection(len(self._selected), len(self._entries))
        except Exception:
            pass

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
