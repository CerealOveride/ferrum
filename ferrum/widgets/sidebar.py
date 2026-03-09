from pathlib import Path
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Tree

from ferrum.messages import DirectoryRequested


PLACES = [
    ("🏠 Home", str(Path.home())),
    ("📁 Desktop", str(Path.home() / "Desktop")),
    ("📁 Documents", str(Path.home() / "Documents")),
    ("📁 Downloads", str(Path.home() / "Downloads")),
    ("📁 Pictures", str(Path.home() / "Pictures")),
    ("📁 Music", str(Path.home() / "Music")),
    ("📁 Videos", str(Path.home() / "Videos")),
]

# Bookmarks to skip since they're already in Places
SKIP_BOOKMARKS = {"home", "root", "desktop", "documents", 
                  "downloads", "pictures", "music", "videos"}


class Sidebar(Widget):
    """Collapsible sidebar with places, bookmarks, and network shares."""

    DEFAULT_CSS = """
    Sidebar {
        width: 30;
        height: 1fr;
        border-right: solid $panel;
        background: $panel;
    }

    Sidebar Tree {
        background: $panel;
        padding: 0 1;
    }

    Sidebar.hidden {
        display: none;
    }
    """

    def __init__(self, bookmarks: dict[str, str] = None, smb_connections: list = None) -> None:
        super().__init__()
        self.bookmarks = bookmarks or {}
        self._shift_held = False
        self._shift_held = False
        self.smb_connections = smb_connections or []

    def compose(self) -> ComposeResult:
        tree = Tree("📂 Ferrum")
        tree.root.expand()
        self._build_tree(tree)
        yield tree

    def _build_tree(self, tree: Tree) -> None:
        """Build the sidebar tree structure."""
        # Places section
        places = tree.root.add("Places", expand=True)
        for label, path in PLACES:
            if Path(path).exists():
                places.add_leaf(label, data={"path": path})

        # Bookmarks section
        bookmarks = tree.root.add("Bookmarks", expand=True)
        user_bookmarks = {
            k: v for k, v in self.bookmarks.items()
            if k.lower() not in SKIP_BOOKMARKS
        }
        if user_bookmarks:
            for name, path in user_bookmarks.items():
                bm_node = bookmarks.add(f"📌 {name}", data={"path": path, "bookmark": name})
                bm_node.add_leaf("  ✕ Remove", data={"action": "remove_bookmark", "bookmark": name})
        bookmarks.add_leaf("+ Add bookmark", data={"action": "add_bookmark"})

        # Network section
        network = tree.root.add("Network", expand=True)
        for conn in self.smb_connections:
            network.add_leaf(
                f"🌐 {conn.name}",
                data={"path": f"//{conn.host}/{conn.share}", "smb": True}
            )
        network.add_leaf("+ Add connection", data={"action": "add_connection"})

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle sidebar item selection."""
        event.stop()
        if event.node.data is None:
            return

        data = event.node.data

        if "action" in data:
            if data["action"] == "add_connection":
                self.app.run_worker(self._add_smb_connection(), exclusive=True)
            elif data["action"] == "add_bookmark":
                self.app.run_worker(self._add_bookmark(), exclusive=True)
            elif data["action"] == "remove_bookmark":
                name = data.get("bookmark", "")
                parent_node = event.node.parent
                self.app.run_worker(self._remove_bookmark(parent_node, name), exclusive=True)
            return

        if "path" in data:
            self.post_message(DirectoryRequested(data["path"]))

    async def _add_smb_connection(self) -> None:
        """Show dialog to add a new SMB connection."""
        from ferrum.widgets.dialogs import SMBConnectionDialog
        from ferrum.backends.smb import SMBConnection, store_credentials
        from textual import work

        result = await self.app.push_screen_wait(SMBConnectionDialog())
        if result:
            # Store credentials in keyring if provided
            if result["username"] and result["password"]:
                store_credentials(
                    result["host"],
                    result["username"],
                    result["password"]
                )

            # Save to user config
            from ferrum.config import save_smb_connection, SMBConnection as ConfigSMBConn
            config_conn = ConfigSMBConn(
                name=result["name"],
                host=result["host"],
                share=result["share"],
                username=result["username"],
            )
            save_smb_connection(config_conn)

            # Add to sidebar tree
            tree = self.query_one(Tree)
            network_node = None
            for child in tree.root.children:
                if child.label.plain == "Network":
                    network_node = child
                    break

            if network_node:
                path = f"//{result['host']}/{result['share']}"
                network_node.add_leaf(
                    f"🌐 {result['name']}",
                    data={"path": path, "smb": True}
                )

            # Navigate to the new share
            path = f"//{result['host']}/{result['share']}"
            self.post_message(DirectoryRequested(path))
            self.app.notify(f"Connecting to {result['name']}...")

    async def _add_bookmark(self) -> None:
        """Add current directory as a bookmark."""
        from ferrum.widgets.dialogs import InputDialog

        # Get current path from the active pane
        try:
            from ferrum.widgets.file_pane import FilePane
            pane = self.app.query_one(FilePane)
            current_path = pane.get_active_pane().current_path
        except Exception:
            self.app.notify("Cannot determine current directory", severity="error")
            return

        from pathlib import Path, PurePosixPath
        from ferrum.backends.router import is_smb_path
        if is_smb_path(current_path):
            default_name = PurePosixPath(current_path).name or current_path
        else:
            default_name = Path(current_path).name or current_path

        result = await self.app.push_screen_wait(
            InputDialog(title="Add Bookmark", placeholder="Bookmark name", initial=default_name)
        )
        if not result:
            return

        name = result.strip()
        if not name:
            return

        # Save to config
        from ferrum.config import save_bookmark
        save_bookmark(name, current_path)

        # Add to sidebar tree
        tree = self.query_one(Tree)
        bookmarks_node = None
        for child in tree.root.children:
            if child.label.plain == "Bookmarks":
                bookmarks_node = child
                break

        if bookmarks_node:
            # Insert before the "+ Add bookmark" leaf
            bookmarks_node.add_leaf(f"📌 {name}", data={"path": current_path})

        self.app.notify(f"Bookmarked: {name}")

    async def _remove_bookmark(self, node, name: str = "") -> None:
        """Remove a bookmark after confirmation."""
        from ferrum.widgets.dialogs import ConfirmDialog
        if not name and node and node.data:
            name = node.data.get("bookmark", "")
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(title="Remove Bookmark", message=f"Remove bookmark '{name}'?")
        )
        if confirmed:
            from ferrum.config import remove_bookmark
            remove_bookmark(name)
            if node:
                node.remove()
            self.app.notify(f"Removed bookmark: {name}")

    async def _add_bookmark(self) -> None:
        """Add current directory as a bookmark."""
        from ferrum.widgets.dialogs import InputDialog

        # Get current path from the active pane
        try:
            from ferrum.widgets.file_pane import FilePane
            pane = self.app.query_one(FilePane)
            current_path = pane.get_active_pane().current_path
        except Exception:
            self.app.notify("Cannot determine current directory", severity="error")
            return

        from pathlib import Path, PurePosixPath
        from ferrum.backends.router import is_smb_path
        if is_smb_path(current_path):
            default_name = PurePosixPath(current_path).name or current_path
        else:
            default_name = Path(current_path).name or current_path

        result = await self.app.push_screen_wait(
            InputDialog(title="Add Bookmark", placeholder="Bookmark name", initial=default_name)
        )
        if not result:
            return

        name = result.strip()
        if not name:
            return

        # Save to config
        from ferrum.config import save_bookmark
        save_bookmark(name, current_path)

        # Add to sidebar tree
        tree = self.query_one(Tree)
        bookmarks_node = None
        for child in tree.root.children:
            if child.label.plain == "Bookmarks":
                bookmarks_node = child
                break

        if bookmarks_node:
            # Insert before the "+ Add bookmark" leaf
            bookmarks_node.add_leaf(f"📌 {name}", data={"path": current_path})

        self.app.notify(f"Bookmarked: {name}")

    def toggle(self) -> None:
        """Show or hide the sidebar."""
        self.toggle_class("hidden")