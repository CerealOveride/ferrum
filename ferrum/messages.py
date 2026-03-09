from textual.message import Message
from pathlib import Path
from dataclasses import dataclass


class DirectoryRequested(Message):
    """Request to navigate to a directory."""
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path


class DirectoryLoaded(Message):
    """Directory contents have been loaded."""
    def __init__(self, path: str, entries: list) -> None:
        super().__init__()
        self.path = path
        self.entries = entries


class DirectoryError(Message):
    """An error occurred loading a directory."""
    def __init__(self, path: str, error: str) -> None:
        super().__init__()
        self.path = path
        self.error = error


class FileSelected(Message):
    """A file has been selected for preview."""
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path


class OperationStarted(Message):
    """A file operation has started."""
    def __init__(self, operation_id: str, description: str) -> None:
        super().__init__()
        self.operation_id = operation_id
        self.description = description


class OperationProgress(Message):
    """Progress update for a file operation."""
    def __init__(self, operation_id: str, progress: float) -> None:
        super().__init__()
        self.operation_id = operation_id
        self.progress = progress


class OperationComplete(Message):
    """A file operation has completed."""
    def __init__(self, operation_id: str) -> None:
        super().__init__()
        self.operation_id = operation_id


class OperationError(Message):
    """A file operation has failed."""
    def __init__(self, operation_id: str, error: str) -> None:
        super().__init__()
        self.operation_id = operation_id
        self.error = error


class StatusMessage(Message):
    """A message to display in the status bar."""
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text