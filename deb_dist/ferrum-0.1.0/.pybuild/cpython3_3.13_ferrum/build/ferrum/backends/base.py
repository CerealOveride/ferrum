from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FileEntry:
    """Represents a single file or directory entry."""
    name: str
    path: str
    is_dir: bool
    size: int
    modified: datetime
    is_hidden: bool
    is_symlink: bool
    extension: str


class FSBackend(ABC):
    """Abstract base class for filesystem backends."""

    @abstractmethod
    async def list_dir(self, path: str) -> list[FileEntry]:
        """List contents of a directory."""
        pass

    @abstractmethod
    async def stat(self, path: str) -> FileEntry:
        """Get metadata for a single path."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if a path exists."""
        pass

    @abstractmethod
    async def is_dir(self, path: str) -> bool:
        """Check if a path is a directory."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete a file or directory."""
        pass

    @abstractmethod
    async def rename(self, src: str, dst: str) -> None:
        """Rename or move a file."""
        pass

    @abstractmethod
    async def mkdir(self, path: str) -> None:
        """Create a directory."""
        pass

    @abstractmethod
    def get_parent(self, path: str) -> str:
        """Get the parent directory of a path."""
        pass

    @abstractmethod
    def join(self, *parts: str) -> str:
        """Join path components."""
        pass