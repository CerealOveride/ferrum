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
        self.smb_connections = smb_connections or []
        self._highlighted_node = None
        self._devices_node = None
        self._device_nodes: dict[str, object] = {}  # obj_path → TreeNode
        self._monitor = None

    def compose(self) -> ComposeResult:
        tree = Tree("📂 Ferrum")
        tree.root.expand()
        self._build_tree(tree)
        yield tree

    def on_mount(self) -> None:
        """Start the device monitor after the widget is mounted."""
        self.app.run_worker(self._start_device_monitor(), exclusive=False)

    def on_unmount(self) -> None:
        """Stop the device monitor when the sidebar is removed."""
        if self._monitor is not None:
            self._monitor.stop()

    async def _start_device_monitor(self) -> None:
        """Fetch initial devices and start the hot-plug signal watcher."""
        from ferrum.devices import DeviceMonitor
        self._monitor = DeviceMonitor(
            on_added=self._on_device_added,
            on_removed=self._on_device_removed,
        )
        try:
            entries = await self._monitor.get_initial()
            for entry in entries:
                self._add_device_node(entry)
        except Exception:
            pass  # D-Bus unavailable — Devices section stays empty
        self._monitor.start()

    def _on_device_added(self, entry) -> None:
        """Called from the DeviceMonitor asyncio task when a device appears."""
        self.call_later(self._add_device_node, entry)

    def _on_device_removed(self, obj_path: str) -> None:
        """Called from the DeviceMonitor asyncio task when a device disappears."""
        self.call_later(self._remove_device_node, obj_path)

    def _add_device_node(self, entry) -> None:
        if self._devices_node is None:
            return
        if entry.obj_path in self._device_nodes:
            return  # already shown
        icon = "💾" if entry.removable else "💿"
        node = self._devices_node.add_leaf(
            f"{icon} {entry.label}",
            data={"path": entry.mount_point},
        )
        self._device_nodes[entry.obj_path] = node

    def _remove_device_node(self, obj_path: str) -> None:
        node = self._device_nodes.pop(obj_path, None)
        if node is not None:
            node.remove()

    def _build_tree(self, tree: Tree) -> None:
        """Build the sidebar tree structure."""
        # Places section
        places = tree.root.add("Places", expand=True)
        for label, path in PLACES:
            if Path(path).exists():
                places.add_leaf(label, data={"path": path})

        # Devices section (populated asynchronously via DeviceMonitor)
        self._devices_node = tree.root.add("Devices", expand=True)

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
                data={
                    "path": f"//{conn.host}/{conn.share}",
                    "smb": True,
                    "smb_name": conn.name,
                    "smb_host": conn.host,
                    "smb_share": conn.share,
                    "smb_username": conn.username,
                }
            )
        network.add_leaf("+ Add connection", data={"action": "add_connection"})

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        """Track the currently highlighted node for key handling."""
        self._highlighted_node = event.node

    def get_highlighted_smb_node(self):
        """Return the highlighted Network SMB share node, or None."""
        node = self._highlighted_node
        if node is None or node.data is None:
            return None
        data = node.data
        if data.get("smb") and "smb_host" in data:
            return node
        return None

    def on_key(self, event) -> None:
        """Handle Delete key to remove a highlighted network share."""
        if event.key != "delete":
            return
        node = self._highlighted_node
        if node is None or node.data is None:
            return
        data = node.data
        if data.get("smb") and "smb_host" in data:
            event.stop()
            self.app.run_worker(self._remove_smb_connection(node), exclusive=True)

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

            # Also register it with the router's in-memory cache, otherwise
            # get_backend_for_path() can't find the username for this share until
            # Ferrum is restarted and connects as guest (credential-prompt loop).
            from ferrum.backends.router import _config_connections
            for i, c in enumerate(_config_connections):
                if c.host == config_conn.host and c.share == config_conn.share:
                    _config_connections[i] = config_conn
                    break
            else:
                _config_connections.append(config_conn)

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
                    data={
                        "path": path,
                        "smb": True,
                        "smb_name": result["name"],
                        "smb_host": result["host"],
                        "smb_share": result["share"],
                        "smb_username": result["username"],
                    }
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
            bm_node = bookmarks_node.add(f"📌 {name}", data={"path": current_path, "bookmark": name})
            bm_node.add_leaf("  ✕ Remove", data={"action": "remove_bookmark", "bookmark": name})

        self.app.notify(f"Bookmarked: {name}")

    async def _remove_smb_connection(self, node) -> None:
        """Remove a saved SMB network share after confirmation."""
        from ferrum.widgets.dialogs import RemoveSMBDialog
        data = node.data
        smb_name = data.get("smb_name", "")
        smb_host = data.get("smb_host", "")
        smb_share = data.get("smb_share", "")
        smb_username = data.get("smb_username", "")

        # Check whether credentials are stored
        from ferrum.backends.smb import get_credentials
        has_creds = bool(smb_username and get_credentials(smb_host, smb_username))

        result = await self.app.push_screen_wait(
            RemoveSMBDialog(smb_name, smb_host, smb_share, has_creds)
        )
        if not result or not result.get("confirm"):
            return

        # Remove from config
        from ferrum.config import remove_smb_connection
        remove_smb_connection(smb_host, smb_share)

        # Optionally clear keyring credentials
        if result.get("clear_credentials") and smb_username:
            from ferrum.backends.smb import delete_credentials
            delete_credentials(smb_host, smb_username)

        # Remove from router's live connection list
        from ferrum.backends.router import _config_connections
        for i, conn in enumerate(_config_connections):
            if conn.host == smb_host and conn.share == smb_share:
                _config_connections.pop(i)
                break

        # Remove node from tree
        node.remove()
        self._highlighted_node = None
        self.app.notify(f"Removed {smb_name}")

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

    def toggle(self) -> None:
        """Show or hide the sidebar."""
        self.toggle_class("hidden")