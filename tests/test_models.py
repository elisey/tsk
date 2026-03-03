"""Tests for data models."""

from datetime import datetime

import pytest

from tsk.models import (
    PRIORITY_CRITICAL,
    PRIORITY_DEFAULT,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    Issue,
    Status,
)


class TestStatus:
    """Tests for Status enum."""

    def test_status_values(self) -> None:
        """Test status enum values."""
        assert Status.TODO.value == "todo"
        assert Status.IN_PROGRESS.value == "in_progress"
        assert Status.CLOSED.value == "closed"


class TestPriorityConstants:
    """Tests for priority constants."""

    def test_priority_order(self) -> None:
        """Test priority ordering (lower is more urgent)."""
        assert PRIORITY_CRITICAL < PRIORITY_MEDIUM < PRIORITY_LOW

    def test_default_priority(self) -> None:
        """Test default priority is medium."""
        assert PRIORITY_DEFAULT == PRIORITY_MEDIUM


class TestIssue:
    """Tests for Issue dataclass."""

    def test_create_minimal_issue(self) -> None:
        """Test creating issue with only required fields."""
        issue = Issue(id=1, title="Test issue", status=Status.TODO)

        assert issue.id == 1
        assert issue.title == "Test issue"
        assert issue.status == Status.TODO
        assert issue.priority == PRIORITY_DEFAULT
        assert issue.description == ""
        assert issue.depends_on == []
        assert issue.closed_at is None

    def test_create_full_issue(self) -> None:
        """Test creating issue with all fields."""
        now = datetime.now()
        issue = Issue(
            id=42,
            title="Full issue",
            status=Status.IN_PROGRESS,
            priority=PRIORITY_CRITICAL,
            description="A detailed description",
            depends_on=[1, 2, 3],
            created_at=now,
            updated_at=now,
            closed_at=None,
        )

        assert issue.id == 42
        assert issue.title == "Full issue"
        assert issue.status == Status.IN_PROGRESS
        assert issue.priority == PRIORITY_CRITICAL
        assert issue.description == "A detailed description"
        assert issue.depends_on == [1, 2, 3]
        assert issue.created_at == now
        assert issue.updated_at == now

    def test_invalid_id_zero(self) -> None:
        """Test that ID must be positive."""
        with pytest.raises(ValueError, match="Issue ID must be positive"):
            Issue(id=0, title="Test", status=Status.TODO)

    def test_invalid_id_negative(self) -> None:
        """Test that negative ID raises error."""
        with pytest.raises(ValueError, match="Issue ID must be positive"):
            Issue(id=-5, title="Test", status=Status.TODO)

    def test_empty_title(self) -> None:
        """Test that empty title raises error."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Issue(id=1, title="", status=Status.TODO)

    def test_whitespace_title(self) -> None:
        """Test that whitespace-only title raises error."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Issue(id=1, title="   ", status=Status.TODO)

    def test_invalid_priority(self) -> None:
        """Test that invalid priority raises error."""
        with pytest.raises(ValueError, match="Invalid priority"):
            Issue(id=1, title="Test", status=Status.TODO, priority=99)

    def test_depends_on_independent(self) -> None:
        """Test that depends_on lists are independent between instances."""
        issue1 = Issue(id=1, title="Issue 1", status=Status.TODO)
        issue2 = Issue(id=2, title="Issue 2", status=Status.TODO)

        issue1.depends_on.append(3)

        assert issue1.depends_on == [3]
        assert issue2.depends_on == []
