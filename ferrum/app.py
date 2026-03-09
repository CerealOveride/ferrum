from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header
from textual.containers import Horizontal
from textual.binding import Binding
from textual import work

from ferrum.config import load_config, ensure_config_dir
from ferrum.widgets.file_pane import FilePane
from ferrum.widgets.sidebar import Sidebar
from ferrum.widgets.preview import PreviewPane
from ferrum.widgets.footer import FerrumFooter
from ferrum.widgets.dialogs import ConflictDialog, ConfirmDialog, InputDialog
from ferrum.messages import DirectoryRequested, FileSelected, FileOpened
from ferrum.operations.manager import OperationsManager
from ferrum.operations.types import ConflictResolution


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
        Binding("ctrl+c", "copy_files", "Copy"),
        Binding("ctrl+x", "cut_files", "Cut"),
        Binding("ctrl+v", "paste_files", "Paste"),
        Binding("delete", "trash_files", "Trash"),
        Binding("shift+delete", "delete_files", "Delete"),
        Binding("f2", "rename_file", "Rename"),
        Binding("f5", "mkdir", "New Dir"),
    ]

    def __init__(self):
        super().__init__()
        ensure_config_dir()
        self.config = load_config()

        # Register config SMB connections with router
        from ferrum.backends.router import set_config_connections
        set_config_connections(self.config.smb_connections)

        self.ops = OperationsManager(
            on_progress=self._on_op_progress,
            on_complete=self._on_op_complete,
            on_error=self._on_op_error,
            on_conflict=self._on_op_conflict,
        )

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="pane-container"):
            yield Sidebar(
                bookmarks=self.config.bookmarks,
                smb_connections=self.config.smb_connections,
            )
            yield FilePane(str(Path.home()))
            yield PreviewPane()
        yield FerrumFooter()

    def on_directory_requested(self, event: DirectoryRequested) -> None:
        self.query_one(FilePane).load_directory(event.path)

    def on_file_selected(self, event: FileSelected) -> None:
        self.query_one(PreviewPane).preview(event.path)

    @work
    async def on_file_opened(self, event: FileOpened) -> None:
        """Open a file with xdg-open."""
        from ferrum.opener import open_file
        # Also update preview
        self.query_one(PreviewPane).preview(event.path)
        try:
            await open_file(event.path)
        except Exception as e:
            self.notify(f"Cannot open file: {e}", severity="error")

    def _get_active_pane(self):
        return self.query_one(FilePane).get_active_pane()

    def _get_selected_paths(self) -> list[str]:
        pane = self._get_active_pane()
        if not pane:
            return []
        table = pane.query_one("FileTable")
        selected = table.get_selected_paths()
        if not selected:
            entry = table.get_selected_entry()
            if entry:
                return [entry.path]
        return selected

    def _get_current_dir(self) -> str:
        pane = self._get_active_pane()
        return pane.current_path if pane else str(Path.home())

    def _refresh_current(self) -> None:
        pane = self._get_active_pane()
        if pane:
            pane.load_directory(pane.current_path)

    async def _on_op_progress(self, op) -> None:
        self.query_one(FerrumFooter).show_progress(op)

    async def _on_op_complete(self, op) -> None:
        self.query_one(FerrumFooter).hide_progress()
        self.notify(f"{op.description} complete")
        self._refresh_current()

    async def _on_op_error(self, op) -> None:
        self.query_one(FerrumFooter).hide_progress()
        self.notify(f"Error: {op.error}", severity="error")

    async def _on_op_conflict(self, dst_path: str) -> ConflictResolution:
        filename = Path(dst_path).name
        result = await self.push_screen_wait(ConflictDialog(filename))
        return result

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

    def action_copy_files(self) -> None:
        paths = self._get_selected_paths()
        if paths:
            self.ops.copy_to_clipboard(paths)
            count = len(paths)
            self.notify(f"{count} {'file' if count == 1 else 'files'} copied to clipboard")

    def action_cut_files(self) -> None:
        paths = self._get_selected_paths()
        if paths:
            self.ops.cut_to_clipboard(paths)
            count = len(paths)
            self.notify(f"{count} {'file' if count == 1 else 'files'} cut to clipboard")

    @work
    async def action_paste_files(self) -> None:
        if not self.ops.clipboard:
            self.notify("Nothing to paste", severity="warning")
            return
        dst = self._get_current_dir()
        await self.ops.paste(dst)

    @work
    async def action_trash_files(self) -> None:
        paths = self._get_selected_paths()
        if not paths:
            return
        count = len(paths)
        noun = "file" if count == 1 else "files"
        confirmed = await self.push_screen_wait(
            ConfirmDialog("Move to Trash", f"Move {count} {noun} to trash?")
        )
        if confirmed:
            await self.ops.trash(paths)

    @work
    async def action_delete_files(self) -> None:
        paths = self._get_selected_paths()
        if not paths:
            return
        count = len(paths)
        noun = "file" if count == 1 else "files"
        confirmed = await self.push_screen_wait(
            ConfirmDialog(
                "Permanently Delete",
                f"Permanently delete {count} {noun}? This cannot be undone."
            )
        )
        if confirmed:
            await self.ops.delete(paths)

    @work
    async def action_rename_file(self) -> None:
        paths = self._get_selected_paths()
        if not paths or len(paths) > 1:
            self.notify("Select a single file to rename", severity="warning")
            return
        src = paths[0]
        src_path = Path(src)
        new_name = await self.push_screen_wait(
            InputDialog("Rename", placeholder="New name", initial=src_path.name)
        )
        if new_name and new_name != src_path.name:
            dst = str(src_path.parent / new_name)
            await self.ops.rename(src, dst)
            self._refresh_current()

    @work
    async def action_mkdir(self) -> None:
        current = self._get_current_dir()
        name = await self.push_screen_wait(
            InputDialog("New Directory", placeholder="Directory name")
        )
        if name:
            dst = str(Path(current) / name)
            await self.ops.mkdir(dst)
            self._refresh_current()
