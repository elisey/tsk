"""Tests for markdown parser."""

from datetime import datetime

import pytest

from tsk.models import (
    PRIORITY_CRITICAL,
    PRIORITY_DEFAULT,
    PRIORITY_LOW,
    Issue,
    Status,
)
from tsk.parser import ParseError, parse_issues, serialize_issues


class TestParseIssues:
    """Tests for parse_issues function."""

    def test_empty_content(self) -> None:
        """Test parsing empty content returns empty list."""
        result = parse_issues("", Status.TODO)
        assert result == []

    def test_whitespace_only_content(self) -> None:
        """Test parsing whitespace-only content returns empty list."""
        result = parse_issues("   \n\n   ", Status.TODO)
        assert result == []

    def test_parse_minimal_issue(self) -> None:
        """Test parsing issue with only required fields."""
        content = """## Issue 1

**Title:** Test issue
"""
        result = parse_issues(content, Status.TODO)

        assert len(result) == 1
        issue = result[0]
        assert issue.id == 1
        assert issue.title == "Test issue"
        assert issue.status == Status.TODO
        assert issue.priority == PRIORITY_DEFAULT
        assert issue.description == ""
        assert issue.depends_on == []

    def test_parse_full_issue(self) -> None:
        """Test parsing issue with all fields."""
        content = """## Issue 42

**Title:** Full issue
**Priority:** 0
**Depends on:** 1, 2, 3
**Created:** 2024-03-15T14:30:00
**Updated:** 2024-03-15T16:45:00

### Description

This is a multiline
description for the issue.
"""
        result = parse_issues(content, Status.IN_PROGRESS)

        assert len(result) == 1
        issue = result[0]
        assert issue.id == 42
        assert issue.title == "Full issue"
        assert issue.status == Status.IN_PROGRESS
        assert issue.priority == PRIORITY_CRITICAL
        assert issue.depends_on == [1, 2, 3]
        assert issue.created_at == datetime(2024, 3, 15, 14, 30, 0)
        assert issue.updated_at == datetime(2024, 3, 15, 16, 45, 0)
        assert "multiline" in issue.description
        assert "description for the issue" in issue.description

    def test_parse_closed_issue(self) -> None:
        """Test parsing closed issue with closed_at field."""
        content = """## Issue 5

**Title:** Closed issue
**Priority:** 1
**Created:** 2024-03-15T14:30:00
**Updated:** 2024-03-15T16:45:00
**Closed:** 2024-03-15T18:00:00
"""
        result = parse_issues(content, Status.CLOSED)

        assert len(result) == 1
        issue = result[0]
        assert issue.closed_at == datetime(2024, 3, 15, 18, 0, 0)

    def test_parse_multiple_issues(self) -> None:
        """Test parsing multiple issues from single file."""
        content = """## Issue 1

**Title:** First issue
**Priority:** 0

## Issue 2

**Title:** Second issue
**Priority:** 2

## Issue 3

**Title:** Third issue
"""
        result = parse_issues(content, Status.TODO)

        assert len(result) == 3
        assert result[0].id == 1
        assert result[0].title == "First issue"
        assert result[0].priority == PRIORITY_CRITICAL
        assert result[1].id == 2
        assert result[1].title == "Second issue"
        assert result[1].priority == PRIORITY_LOW
        assert result[2].id == 3
        assert result[2].title == "Third issue"
        assert result[2].priority == PRIORITY_DEFAULT

    def test_parse_issue_flexible_field_order(self) -> None:
        """Test that fields can be in any order."""
        content = """## Issue 1

**Created:** 2024-03-15T14:30:00
**Priority:** 2
**Depends on:** 5
**Title:** Flexible order
**Updated:** 2024-03-15T16:45:00
"""
        result = parse_issues(content, Status.TODO)

        assert len(result) == 1
        issue = result[0]
        assert issue.title == "Flexible order"
        assert issue.priority == PRIORITY_LOW
        assert issue.depends_on == [5]

    def test_missing_title_raises_error(self) -> None:
        """Test that missing title raises ParseError."""
        content = """## Issue 1

**Priority:** 1
"""
        with pytest.raises(ParseError, match="missing required Title"):
            parse_issues(content, Status.TODO)

    def test_default_priority_when_missing(self) -> None:
        """Test that missing priority defaults to P1."""
        content = """## Issue 1

**Title:** No priority set
"""
        result = parse_issues(content, Status.TODO)

        assert result[0].priority == PRIORITY_DEFAULT

    def test_parse_single_dependency(self) -> None:
        """Test parsing issue with single dependency."""
        content = """## Issue 2

**Title:** Single dep
**Depends on:** 1
"""
        result = parse_issues(content, Status.TODO)

        assert result[0].depends_on == [1]

    def test_parse_empty_depends_on(self) -> None:
        """Test parsing empty depends_on field."""
        content = """## Issue 1

**Title:** No deps
**Depends on:**
"""
        result = parse_issues(content, Status.TODO)

        assert result[0].depends_on == []

    def test_description_multiline(self) -> None:
        """Test that multiline descriptions are preserved."""
        content = """## Issue 1

**Title:** With description

### Description

Line 1
Line 2

Line 4 after blank
"""
        result = parse_issues(content, Status.TODO)

        desc = result[0].description
        assert "Line 1" in desc
        assert "Line 2" in desc
        assert "Line 4 after blank" in desc


class TestSerializeIssues:
    """Tests for serialize_issues function."""

    def test_empty_list(self) -> None:
        """Test serializing empty list returns empty string."""
        result = serialize_issues([])
        assert result == ""

    def test_serialize_minimal_issue(self) -> None:
        """Test serializing issue with minimal fields."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=1,
            title="Test issue",
            status=Status.TODO,
            created_at=now,
            updated_at=now,
        )

        result = serialize_issues([issue])

        assert "## Issue 1" in result
        assert "**Title:** Test issue" in result
        assert "**Priority:** 1" in result
        assert "**Created:** 2024-03-15T14:30:00" in result
        assert "**Updated:** 2024-03-15T14:30:00" in result

    def test_serialize_with_dependencies(self) -> None:
        """Test serializing issue with dependencies."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=5,
            title="With deps",
            status=Status.TODO,
            depends_on=[1, 2, 3],
            created_at=now,
            updated_at=now,
        )

        result = serialize_issues([issue])

        assert "**Depends on:** 1, 2, 3" in result

    def test_serialize_with_description(self) -> None:
        """Test serializing issue with description."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issue = Issue(
            id=1,
            title="With desc",
            status=Status.TODO,
            description="A detailed description",
            created_at=now,
            updated_at=now,
        )

        result = serialize_issues([issue])

        assert "### Description" in result
        assert "A detailed description" in result

    def test_serialize_closed_issue(self) -> None:
        """Test serializing closed issue includes closed_at."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        closed = datetime(2024, 3, 15, 18, 0, 0)
        issue = Issue(
            id=1,
            title="Closed",
            status=Status.CLOSED,
            created_at=now,
            updated_at=now,
            closed_at=closed,
        )

        result = serialize_issues([issue])

        assert "**Closed:** 2024-03-15T18:00:00" in result

    def test_serialize_multiple_issues(self) -> None:
        """Test serializing multiple issues."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        issues = [
            Issue(
                id=1, title="First", status=Status.TODO, created_at=now, updated_at=now
            ),
            Issue(
                id=2, title="Second", status=Status.TODO, created_at=now, updated_at=now
            ),
        ]

        result = serialize_issues(issues)

        assert "## Issue 1" in result
        assert "## Issue 2" in result
        assert "**Title:** First" in result
        assert "**Title:** Second" in result

    def test_roundtrip(self) -> None:
        """Test that serialize then parse gives equivalent issues."""
        now = datetime(2024, 3, 15, 14, 30, 0)
        original = Issue(
            id=42,
            title="Roundtrip test",
            status=Status.TODO,
            priority=PRIORITY_CRITICAL,
            description="A description",
            depends_on=[1, 2],
            created_at=now,
            updated_at=now,
        )

        serialized = serialize_issues([original])
        parsed = parse_issues(serialized, Status.TODO)

        assert len(parsed) == 1
        result = parsed[0]
        assert result.id == original.id
        assert result.title == original.title
        assert result.priority == original.priority
        assert result.description == original.description
        assert result.depends_on == original.depends_on
        assert result.created_at == original.created_at
        assert result.updated_at == original.updated_at
