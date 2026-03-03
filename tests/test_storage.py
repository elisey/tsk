"""Tests for storage layer."""

from datetime import datetime
from pathlib import Path

import pytest

from tsk.fs import init_tsk_dir
from tsk.models import Issue, Status
from tsk.parser import serialize_issues
from tsk.storage import (
    DependencyError,
    IssueNotFoundError,
    add_dependency,
    find_issue,
    get_next_id,
    has_cycle,
    load_all_issues,
    move_issue,
    remove_dependency,
    save_issues,
)


@pytest.fixture
def tsk_dir(tmp_path: Path) -> Path:
    """Create and return a .tsk/ directory."""
    return init_tsk_dir(tmp_path)


class TestLoadAllIssues:
    """Tests for load_all_issues function."""

    def test_empty_files(self, tsk_dir: Path) -> None:
        """Test loading from empty files returns empty lists."""
        result = load_all_issues(tsk_dir)

        assert result[Status.TODO] == []
        assert result[Status.IN_PROGRESS] == []
        assert result[Status.CLOSED] == []

    def test_load_issues_from_files(self, tsk_dir: Path) -> None:
        """Test loading issues from files."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        todo_issue = Issue(
            id=1, title="Todo", status=Status.TODO, created_at=now, updated_at=now
        )
        (tsk_dir / "todo.md").write_text(serialize_issues([todo_issue]))

        result = load_all_issues(tsk_dir)

        assert len(result[Status.TODO]) == 1
        assert result[Status.TODO][0].id == 1
        assert result[Status.TODO][0].title == "Todo"


class TestSaveIssues:
    """Tests for save_issues function."""

    def test_save_to_empty_file(self, tsk_dir: Path) -> None:
        """Test saving issues to empty file."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=1, title="New issue", status=Status.TODO, created_at=now, updated_at=now
        )

        save_issues(Status.TODO, [issue], tsk_dir)

        content = (tsk_dir / "todo.md").read_text()
        assert "## Issue 1" in content
        assert "**Title:** New issue" in content

    def test_save_multiple_issues(self, tsk_dir: Path) -> None:
        """Test saving multiple issues."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issues = [
            Issue(
                id=1, title="First", status=Status.TODO, created_at=now, updated_at=now
            ),
            Issue(
                id=2, title="Second", status=Status.TODO, created_at=now, updated_at=now
            ),
        ]

        save_issues(Status.TODO, issues, tsk_dir)

        content = (tsk_dir / "todo.md").read_text()
        assert "## Issue 1" in content
        assert "## Issue 2" in content


class TestGetNextId:
    """Tests for get_next_id function."""

    def test_empty_returns_one(self, tsk_dir: Path) -> None:
        """Test that empty storage returns ID 1."""
        result = get_next_id(tsk_dir)
        assert result == 1

    def test_increments_max_id(self, tsk_dir: Path) -> None:
        """Test that next ID is max + 1."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issues = [
            Issue(
                id=5, title="Five", status=Status.TODO, created_at=now, updated_at=now
            ),
            Issue(
                id=3, title="Three", status=Status.TODO, created_at=now, updated_at=now
            ),
        ]
        save_issues(Status.TODO, issues, tsk_dir)

        result = get_next_id(tsk_dir)
        assert result == 6

    def test_considers_all_statuses(self, tsk_dir: Path) -> None:
        """Test that max ID considers all status files."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        todo = Issue(
            id=2, title="Todo", status=Status.TODO, created_at=now, updated_at=now
        )
        closed = Issue(
            id=10, title="Closed", status=Status.CLOSED, created_at=now, updated_at=now
        )
        save_issues(Status.TODO, [todo], tsk_dir)
        save_issues(Status.CLOSED, [closed], tsk_dir)

        result = get_next_id(tsk_dir)
        assert result == 11


class TestFindIssue:
    """Tests for find_issue function."""

    def test_find_existing_issue(self, tsk_dir: Path) -> None:
        """Test finding an existing issue."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=5, title="Found me", status=Status.TODO, created_at=now, updated_at=now
        )
        save_issues(Status.TODO, [issue], tsk_dir)

        found, status = find_issue(5, tsk_dir)

        assert found.id == 5
        assert found.title == "Found me"
        assert status == Status.TODO

    def test_find_in_different_status(self, tsk_dir: Path) -> None:
        """Test finding issue in different status file."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=3,
            title="In progress",
            status=Status.IN_PROGRESS,
            created_at=now,
            updated_at=now,
        )
        save_issues(Status.IN_PROGRESS, [issue], tsk_dir)

        found, status = find_issue(3, tsk_dir)

        assert found.id == 3
        assert status == Status.IN_PROGRESS

    def test_not_found_raises_error(self, tsk_dir: Path) -> None:
        """Test that missing issue raises IssueNotFoundError."""
        with pytest.raises(IssueNotFoundError, match="Issue 99 not found"):
            find_issue(99, tsk_dir)


class TestMoveIssue:
    """Tests for move_issue function."""

    def test_move_to_different_status(self, tsk_dir: Path) -> None:
        """Test moving issue to different status."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=1, title="Move me", status=Status.TODO, created_at=now, updated_at=now
        )
        save_issues(Status.TODO, [issue], tsk_dir)

        result = move_issue(1, Status.IN_PROGRESS, tsk_dir)

        assert result.status == Status.IN_PROGRESS
        assert result.updated_at > now

        # Verify files
        all_issues = load_all_issues(tsk_dir)
        assert len(all_issues[Status.TODO]) == 0
        assert len(all_issues[Status.IN_PROGRESS]) == 1
        assert all_issues[Status.IN_PROGRESS][0].id == 1

    def test_move_to_closed_sets_closed_at(self, tsk_dir: Path) -> None:
        """Test that moving to closed sets closed_at."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=1, title="Close me", status=Status.TODO, created_at=now, updated_at=now
        )
        save_issues(Status.TODO, [issue], tsk_dir)

        result = move_issue(1, Status.CLOSED, tsk_dir)

        assert result.closed_at is not None
        assert result.closed_at > now

    def test_reopen_clears_closed_at(self, tsk_dir: Path) -> None:
        """Test that reopening clears closed_at."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=1,
            title="Reopen me",
            status=Status.CLOSED,
            created_at=now,
            updated_at=now,
            closed_at=now,
        )
        save_issues(Status.CLOSED, [issue], tsk_dir)

        result = move_issue(1, Status.TODO, tsk_dir)

        assert result.closed_at is None

    def test_move_same_status_noop(self, tsk_dir: Path) -> None:
        """Test that moving to same status is a no-op."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=1, title="Stay here", status=Status.TODO, created_at=now, updated_at=now
        )
        save_issues(Status.TODO, [issue], tsk_dir)

        result = move_issue(1, Status.TODO, tsk_dir)

        # Should return original issue unchanged
        assert result.updated_at == now

    def test_move_not_found_raises_error(self, tsk_dir: Path) -> None:
        """Test that moving nonexistent issue raises error."""
        with pytest.raises(IssueNotFoundError):
            move_issue(99, Status.CLOSED, tsk_dir)


class TestHasCycle:
    """Tests for has_cycle function."""

    def test_simple_no_cycle(self, tsk_dir: Path) -> None:
        """Test that non-cyclic dependency returns False."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issues = [
            Issue(id=1, title="A", status=Status.TODO, created_at=now, updated_at=now),
            Issue(id=2, title="B", status=Status.TODO, created_at=now, updated_at=now),
        ]
        save_issues(Status.TODO, issues, tsk_dir)

        assert has_cycle(2, 1, tsk_dir) is False

    def test_simple_cycle(self, tsk_dir: Path) -> None:
        """Test that A->B->A is detected as cycle."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issues = [
            Issue(
                id=1,
                title="A",
                status=Status.TODO,
                depends_on=[2],
                created_at=now,
                updated_at=now,
            ),
            Issue(id=2, title="B", status=Status.TODO, created_at=now, updated_at=now),
        ]
        save_issues(Status.TODO, issues, tsk_dir)

        # Adding 2->1 would create cycle: 2->1->2
        assert has_cycle(2, 1, tsk_dir) is True

    def test_long_cycle(self, tsk_dir: Path) -> None:
        """Test that A->B->C->A is detected."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issues = [
            Issue(
                id=1,
                title="A",
                status=Status.TODO,
                depends_on=[2],
                created_at=now,
                updated_at=now,
            ),
            Issue(
                id=2,
                title="B",
                status=Status.TODO,
                depends_on=[3],
                created_at=now,
                updated_at=now,
            ),
            Issue(id=3, title="C", status=Status.TODO, created_at=now, updated_at=now),
        ]
        save_issues(Status.TODO, issues, tsk_dir)

        # Adding 3->1 would create cycle: 3->1->2->3
        assert has_cycle(3, 1, tsk_dir) is True


class TestAddDependency:
    """Tests for add_dependency function."""

    def test_add_dependency(self, tsk_dir: Path) -> None:
        """Test successfully adding a dependency."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issues = [
            Issue(id=1, title="A", status=Status.TODO, created_at=now, updated_at=now),
            Issue(id=2, title="B", status=Status.TODO, created_at=now, updated_at=now),
        ]
        save_issues(Status.TODO, issues, tsk_dir)

        add_dependency(1, 2, tsk_dir)

        issue, _ = find_issue(1, tsk_dir)
        assert 2 in issue.depends_on

    def test_self_reference_error(self, tsk_dir: Path) -> None:
        """Test that self-reference raises error."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=1, title="A", status=Status.TODO, created_at=now, updated_at=now
        )
        save_issues(Status.TODO, [issue], tsk_dir)

        with pytest.raises(DependencyError, match="cannot depend on itself"):
            add_dependency(1, 1, tsk_dir)

    def test_duplicate_error(self, tsk_dir: Path) -> None:
        """Test that duplicate dependency raises error."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issues = [
            Issue(
                id=1,
                title="A",
                status=Status.TODO,
                depends_on=[2],
                created_at=now,
                updated_at=now,
            ),
            Issue(id=2, title="B", status=Status.TODO, created_at=now, updated_at=now),
        ]
        save_issues(Status.TODO, issues, tsk_dir)

        with pytest.raises(DependencyError, match="already depends"):
            add_dependency(1, 2, tsk_dir)

    def test_nonexistent_issue_error(self, tsk_dir: Path) -> None:
        """Test that nonexistent issue raises error."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=1, title="A", status=Status.TODO, created_at=now, updated_at=now
        )
        save_issues(Status.TODO, [issue], tsk_dir)

        with pytest.raises(IssueNotFoundError):
            add_dependency(1, 99, tsk_dir)

    def test_cycle_error(self, tsk_dir: Path) -> None:
        """Test that creating a cycle raises error."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issues = [
            Issue(
                id=1,
                title="A",
                status=Status.TODO,
                depends_on=[2],
                created_at=now,
                updated_at=now,
            ),
            Issue(id=2, title="B", status=Status.TODO, created_at=now, updated_at=now),
        ]
        save_issues(Status.TODO, issues, tsk_dir)

        with pytest.raises(DependencyError, match="cycle"):
            add_dependency(2, 1, tsk_dir)


class TestRemoveDependency:
    """Tests for remove_dependency function."""

    def test_remove_dependency(self, tsk_dir: Path) -> None:
        """Test successfully removing a dependency."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issues = [
            Issue(
                id=1,
                title="A",
                status=Status.TODO,
                depends_on=[2],
                created_at=now,
                updated_at=now,
            ),
            Issue(id=2, title="B", status=Status.TODO, created_at=now, updated_at=now),
        ]
        save_issues(Status.TODO, issues, tsk_dir)

        remove_dependency(1, 2, tsk_dir)

        issue, _ = find_issue(1, tsk_dir)
        assert 2 not in issue.depends_on

    def test_nonexistent_dependency_error(self, tsk_dir: Path) -> None:
        """Test that removing nonexistent dependency raises error."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=1, title="A", status=Status.TODO, created_at=now, updated_at=now
        )
        save_issues(Status.TODO, [issue], tsk_dir)

        with pytest.raises(DependencyError, match="does not depend"):
            remove_dependency(1, 2, tsk_dir)
