"""Data models for tsk issue tracker."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Status(Enum):
    """Issue status."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


# Priority constants
PRIORITY_CRITICAL = 0
PRIORITY_MEDIUM = 1
PRIORITY_LOW = 2
PRIORITY_DEFAULT = PRIORITY_MEDIUM


@dataclass
class Issue:
    """Represents a single issue/task."""

    id: int
    title: str
    status: Status
    priority: int = PRIORITY_DEFAULT
    description: str = ""
    depends_on: list[int] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    closed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate issue fields."""
        if self.id < 1:
            raise ValueError(f"Issue ID must be positive, got {self.id}")
        if not self.title.strip():
            raise ValueError("Issue title cannot be empty")
        if self.priority not in (PRIORITY_CRITICAL, PRIORITY_MEDIUM, PRIORITY_LOW):
            raise ValueError(f"Invalid priority: {self.priority}")
