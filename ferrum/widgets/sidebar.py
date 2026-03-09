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
                bookmarks.add_leaf(f"📌 {name}", data={"path": path})
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
            self.app.notify(f"Coming soon: {data['action']}")
            return

        if "path" in data:
            self.post_message(DirectoryRequested(data["path"]))

    def toggle(self) -> None:
        """Show or hide the sidebar."""
        self.toggle_class("hidden")