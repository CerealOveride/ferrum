from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class OperationType(Enum):
    COPY = "copy"
    MOVE = "move"
    DELETE = "delete"
    TRASH = "trash"
    RENAME = "rename"
    MKDIR = "mkdir"


class OperationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConflictResolution(Enum):
    ASK = "ask"
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"


@dataclass
class FileOperation:
    """Represents a single file operation."""
    id: str
    type: OperationType
    sources: list[str]
    destination: str | None = None
    status: OperationStatus = OperationStatus.PENDING
    progress: float = 0.0
    current_file: str = ""
    total_files: int = 0
    completed_files: int = 0
    error: str | None = None
    conflict_resolution: ConflictResolution = ConflictResolution.ASK

    @property
    def description(self) -> str:
        count = len(self.sources)
        noun = "file" if count == 1 else "files"
        match self.type:
            case OperationType.COPY:
                return f"Copying {count} {noun}"
            case OperationType.MOVE:
                return f"Moving {count} {noun}"
            case OperationType.DELETE:
                return f"Deleting {count} {noun}"
            case OperationType.TRASH:
                return f"Trashing {count} {noun}"
            case OperationType.RENAME:
                return f"Renaming {self.sources[0]}"
            case OperationType.MKDIR:
                return f"Creating directory"
            case _:
                return "Working..."


@dataclass
class ClipboardEntry:
    """Files staged for copy or move."""
    paths: list[str]
    mode: OperationType  # COPY or MOVE