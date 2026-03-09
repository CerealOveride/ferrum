from pathlib import Path
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import TabbedContent, TabPane
from textual import on, work

from ferrum.backends.local import LocalBackend
from ferrum.backends.router import get_backend_for_path, is_smb_path
from ferrum.widgets.file_table import FileTable
from ferrum.widgets.path_bar import PathBar
from ferrum.messages import DirectoryRequested, DirectoryLoaded, DirectoryError, FileSelected, FileOpened
from ferrum.widgets.preview import PreviewPane


class SinglePane(Widget):
    """A single tab's content — path bar + file table."""

    DEFAULT_CSS = """
    SinglePane {
        height: 1fr;
        width: 1fr;
        layout: vertical;
    }
    """

    def __init__(self, initial_path: str, pane_id: str) -> None:
        super().__init__(id=pane_id)
        if is_smb_path(initial_path):
            self.current_path = initial_path
        else:
            self.current_path = str(Path(initial_path).expanduser().resolve())
        self.backend = get_backend_for_path(self.current_path)
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
        previous_path = self.current_path
        try:
            # Switch backend if path type changed
            self.backend = get_backend_for_path(path)
            entries = await self.backend.list_dir(path)
            self.current_path = path
            self.post_message(DirectoryLoaded(path, entries))
        except (PermissionError, FileNotFoundError, ConnectionError, OSError, Exception) as e:
            # Stay on current directory, don't blank the screen
            self.backend = get_backend_for_path(previous_path)
            self.post_message(DirectoryError(path, str(e)))

    @on(DirectoryLoaded)
    def on_directory_loaded(self, event: DirectoryLoaded) -> None:
        event.stop()
        self.query_one(PathBar).update_path(event.path)
        self.query_one(FileTable).populate(event.entries, self.show_hidden)
        # Update the parent TabPane label to reflect current directory
        from textual.widgets import TabPane, TabbedContent
        from pathlib import PurePosixPath
        try:
            tab_pane = self.parent
            if isinstance(tab_pane, TabPane):
                if is_smb_path(event.path):
                    label = PurePosixPath(event.path).name or event.path
                else:
                    label = Path(event.path).name or event.path
                tabbed = tab_pane.parent.parent  # TabPane → ContentSwitcher → TabbedContent
                if isinstance(tabbed, TabbedContent):
                    tabbed.get_tab(tab_pane.id).label = label
        except Exception:
            pass

    @on(DirectoryError)
    def on_directory_error(self, event: DirectoryError) -> None:
        event.stop()
        self.app.notify(f"Error: {event.error}", severity="error")

    def navigate_up(self) -> None:
        parent = self.backend.get_parent(self.current_path)
        if parent != self.current_path:
            self._history.append(self.current_path)
            self.load_directory(parent)

    def navigate_back(self) -> None:
        if self._history:
            path = self._history.pop()
            self.load_directory(path)


class FilePane(Widget):
    """File pane with tab support."""

    DEFAULT_CSS = """
    FilePane {
        height: 1fr;
        width: 1fr;
        border: solid $panel;
    }

    FilePane TabbedContent {
        height: 1fr;
    }

    FilePane TabbedContent ContentSwitcher {
        height: 1fr;
    }

    FilePane TabPane {
        height: 1fr;
        padding: 0;
    }
    """

    def __init__(self, initial_path: str = "~") -> None:
        super().__init__()
        self.initial_path = str(Path(initial_path).expanduser().resolve())
        self._tab_count = 0

    def compose(self) -> ComposeResult:
        with TabbedContent():
            yield from self._make_tab(self.initial_path)

    def _make_tab(self, path: str):
        """Create a new tab pane for the given path."""
        self._tab_count += 1
        label = Path(path).name or path
        pane_id = f"pane-{self._tab_count}"
        with TabPane(label, id=f"tab-{self._tab_count}"):
            yield SinglePane(path, pane_id)

    def get_active_pane(self) -> SinglePane | None:
        """Get the currently active SinglePane."""
        try:
            tabbed = self.query_one(TabbedContent)
            active_tab_id = tabbed.active
            if not active_tab_id:
                return None
            tab_pane = self.query_one(f"#{active_tab_id}", TabPane)
            return tab_pane.query_one(SinglePane)
        except Exception:
            return None

    def new_tab(self, path: str = None) -> None:
        """Open a new tab."""
        active = self.get_active_pane()
        new_path = path or (active.current_path if active else str(Path.home()))
        tabbed = self.query_one(TabbedContent)
        self._tab_count += 1
        label = Path(new_path).name or new_path
        pane_id = f"pane-{self._tab_count}"
        tab_id = f"tab-{self._tab_count}"
        pane = SinglePane(new_path, pane_id)
        tabbed.add_pane(TabPane(label, pane, id=tab_id))
        tabbed.active = tab_id

    def close_tab(self) -> None:
        """Close the current tab."""
        tabbed = self.query_one(TabbedContent)
        if tabbed.tab_count <= 1:
            self.app.notify("Cannot close the last tab")
            return
        active_id = tabbed.active
        if active_id:
            tabbed.remove_pane(active_id)

    def load_directory(self, path: str) -> None:
        """Load a directory in the active pane."""
        pane = self.get_active_pane()
        if pane:
            pane._history.append(pane.current_path)
            pane.load_directory(path)

    def navigate_up(self) -> None:
        pane = self.get_active_pane()
        if pane:
            pane.navigate_up()

    @on(DirectoryRequested)
    def on_directory_requested(self, event: DirectoryRequested) -> None:
        event.stop()
        pane = self.get_active_pane()
        if pane:
            pane._history.append(pane.current_path)
            pane.load_directory(event.path)

    @on(FileSelected)
    def on_file_selected(self, event: FileSelected) -> None:
        event.stop()
        # Forward directly to the app
        self.app.query_one(PreviewPane).preview(event.path)