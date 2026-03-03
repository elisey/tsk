"""Markdown parsing and serialization for issues."""

import re
from datetime import datetime

from tsk.models import PRIORITY_DEFAULT, Issue, Status


class ParseError(Exception):
    """Raised when markdown parsing fails."""

    pass


def parse_issues(content: str, status: Status) -> list[Issue]:
    """
    Parse markdown content into a list of issues.

    Args:
        content: Markdown file content.
        status: Status to assign to parsed issues.

    Returns:
        List of parsed Issue objects.

    Raises:
        ParseError: If the content cannot be parsed.
    """
    if not content.strip():
        return []

    issues: list[Issue] = []

    # Split by ## Issue headers
    issue_pattern = re.compile(r"^## Issue (\d+)\s*$", re.MULTILINE)
    matches = list(issue_pattern.finditer(content))

    if not matches:
        # Check if there's any content that looks like it should be an issue
        if "## Issue" in content or "**Title:**" in content:
            raise ParseError("Malformed issue format")
        return []

    for i, match in enumerate(matches):
        issue_id = int(match.group(1))

        # Get content between this header and next header (or end)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        issue_content = content[start:end].strip()

        issue = _parse_single_issue(issue_id, issue_content, status)
        issues.append(issue)

    return issues


def _parse_single_issue(issue_id: int, content: str, status: Status) -> Issue:
    """Parse a single issue's content into an Issue object."""
    title = _extract_field(content, "Title")
    if not title:
        raise ParseError(f"Issue {issue_id}: missing required Title field")

    priority_str = _extract_field(content, "Priority")
    priority = int(priority_str) if priority_str else PRIORITY_DEFAULT

    depends_on_str = _extract_field(content, "Depends on")
    depends_on: list[int] = []
    if depends_on_str:
        depends_on = [int(x.strip()) for x in depends_on_str.split(",") if x.strip()]

    created_str = _extract_field(content, "Created")
    created_at = _parse_datetime(created_str) if created_str else datetime.now()

    updated_str = _extract_field(content, "Updated")
    updated_at = _parse_datetime(updated_str) if updated_str else datetime.now()

    closed_str = _extract_field(content, "Closed")
    closed_at = _parse_datetime(closed_str) if closed_str else None

    description = _extract_description(content)

    return Issue(
        id=issue_id,
        title=title,
        status=status,
        priority=priority,
        description=description,
        depends_on=depends_on,
        created_at=created_at,
        updated_at=updated_at,
        closed_at=closed_at,
    )


def _extract_field(content: str, field_name: str) -> str | None:
    """Extract a field value from issue content."""
    pattern = re.compile(rf"^\*\*{field_name}:\*\*\s*(.+)$", re.MULTILINE)
    match = pattern.search(content)
    return match.group(1).strip() if match else None


def _extract_description(content: str) -> str:
    """Extract the description section from issue content."""
    pattern = re.compile(r"^### Description\s*$", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        return ""

    # Get everything after "### Description"
    desc_start = match.end()
    desc_content = content[desc_start:].strip()

    # Remove any trailing sections (shouldn't be any, but just in case)
    return desc_content


def _parse_datetime(dt_str: str) -> datetime:
    """Parse ISO 8601 datetime string."""
    return datetime.fromisoformat(dt_str)


def serialize_issues(issues: list[Issue]) -> str:
    """
    Serialize a list of issues to markdown format.

    Args:
        issues: List of Issue objects to serialize.

    Returns:
        Markdown string representation.
    """
    if not issues:
        return ""

    parts = [_serialize_single_issue(issue) for issue in issues]
    return "\n".join(parts)


def _serialize_single_issue(issue: Issue) -> str:
    """Serialize a single issue to markdown."""
    lines = [
        f"## Issue {issue.id}",
        "",
        f"**Title:** {issue.title}",
        f"**Priority:** {issue.priority}",
    ]

    if issue.depends_on:
        deps_str = ", ".join(str(d) for d in issue.depends_on)
        lines.append(f"**Depends on:** {deps_str}")

    lines.append(f"**Created:** {_format_datetime(issue.created_at)}")
    lines.append(f"**Updated:** {_format_datetime(issue.updated_at)}")

    if issue.closed_at:
        lines.append(f"**Closed:** {_format_datetime(issue.closed_at)}")

    if issue.description:
        lines.extend(["", "### Description", "", issue.description])

    lines.append("")  # Trailing newline
    return "\n".join(lines)


def _format_datetime(dt: datetime) -> str:
    """Format datetime to ISO 8601 string without microseconds."""
    return dt.replace(microsecond=0).isoformat()
