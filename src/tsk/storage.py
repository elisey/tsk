"""Storage layer for issues."""

from dataclasses import replace
from datetime import datetime
from pathlib import Path

from tsk.fs import CLOSED_FILE, IN_PROGRESS_FILE, TODO_FILE, find_tsk_dir
from tsk.models import Issue, Status
from tsk.parser import parse_issues, serialize_issues


class IssueNotFoundError(Exception):
    """Raised when an issue is not found."""


class DependencyError(Exception):
    """Raised when there's a dependency-related error."""


# Map status to filename
STATUS_TO_FILE = {
    Status.TODO: TODO_FILE,
    Status.IN_PROGRESS: IN_PROGRESS_FILE,
    Status.CLOSED: CLOSED_FILE,
}

# Map filename to status
FILE_TO_STATUS = {v: k for k, v in STATUS_TO_FILE.items()}


def load_all_issues(tsk_dir: Path | None = None) -> dict[Status, list[Issue]]:
    """
    Load all issues from all status files.

    Args:
        tsk_dir: Path to .tsk/ directory. If None, will search for it.

    Returns:
        Dictionary mapping status to list of issues.
    """
    if tsk_dir is None:
        tsk_dir = find_tsk_dir()

    result: dict[Status, list[Issue]] = {}

    for status, filename in STATUS_TO_FILE.items():
        file_path = tsk_dir / filename
        content = file_path.read_text() if file_path.exists() else ""
        result[status] = parse_issues(content, status)

    return result


def save_issues(
    status: Status, issues: list[Issue], tsk_dir: Path | None = None
) -> None:
    """
    Save issues to the appropriate status file.

    Args:
        status: Status file to write to.
        issues: List of issues to save.
        tsk_dir: Path to .tsk/ directory. If None, will search for it.
    """
    if tsk_dir is None:
        tsk_dir = find_tsk_dir()

    filename = STATUS_TO_FILE[status]
    file_path = tsk_dir / filename

    content = serialize_issues(issues)
    file_path.write_text(content)


def get_next_id(tsk_dir: Path | None = None) -> int:
    """
    Get the next available issue ID.

    Args:
        tsk_dir: Path to .tsk/ directory. If None, will search for it.

    Returns:
        Next available ID (max existing ID + 1, or 1 if no issues).
    """
    all_issues = load_all_issues(tsk_dir)

    max_id = 0
    for issues in all_issues.values():
        for issue in issues:
            if issue.id > max_id:
                max_id = issue.id

    return max_id + 1


def find_issue(issue_id: int, tsk_dir: Path | None = None) -> tuple[Issue, Status]:
    """
    Find an issue by ID.

    Args:
        issue_id: The issue ID to find.
        tsk_dir: Path to .tsk/ directory. If None, will search for it.

    Returns:
        Tuple of (issue, status).

    Raises:
        IssueNotFoundError: If issue is not found.
    """
    all_issues = load_all_issues(tsk_dir)

    for status, issues in all_issues.items():
        for issue in issues:
            if issue.id == issue_id:
                return (issue, status)

    raise IssueNotFoundError(f"Issue {issue_id} not found")


def move_issue(issue_id: int, new_status: Status, tsk_dir: Path | None = None) -> Issue:
    """
    Move an issue to a new status file.

    Args:
        issue_id: The issue ID to move.
        new_status: The new status.
        tsk_dir: Path to .tsk/ directory. If None, will search for it.

    Returns:
        The updated issue.

    Raises:
        IssueNotFoundError: If issue is not found.
    """
    if tsk_dir is None:
        tsk_dir = find_tsk_dir()

    issue, current_status = find_issue(issue_id, tsk_dir)

    if current_status == new_status:
        return issue

    # Remove from current file
    all_issues = load_all_issues(tsk_dir)
    current_issues = [i for i in all_issues[current_status] if i.id != issue_id]
    save_issues(current_status, current_issues, tsk_dir)

    # Update issue fields
    now = datetime.now()
    updated_issue = replace(issue, status=new_status, updated_at=now)

    if new_status == Status.CLOSED and updated_issue.closed_at is None:
        updated_issue = replace(updated_issue, closed_at=now)
    elif new_status != Status.CLOSED:
        updated_issue = replace(updated_issue, closed_at=None)

    # Add to new file
    new_issues = all_issues[new_status] + [updated_issue]
    save_issues(new_status, new_issues, tsk_dir)

    return updated_issue


def has_cycle(
    issue_id: int,
    new_dep_id: int,
    tsk_dir: Path | None = None,
) -> bool:
    """
    Check if adding a dependency would create a cycle.

    Args:
        issue_id: The issue that would depend on new_dep_id.
        new_dep_id: The issue that would become a dependency.
        tsk_dir: Path to .tsk/ directory.

    Returns:
        True if adding this dependency would create a cycle.
    """
    all_issues = load_all_issues(tsk_dir)

    # Build a map of issue_id -> depends_on
    deps_map: dict[int, list[int]] = {}
    for issues in all_issues.values():
        for issue in issues:
            deps_map[issue.id] = issue.depends_on.copy()

    # Temporarily add the new dependency
    if issue_id in deps_map:
        deps_map[issue_id] = deps_map[issue_id] + [new_dep_id]
    else:
        deps_map[issue_id] = [new_dep_id]

    # DFS to check for cycle starting from issue_id
    visited: set[int] = set()
    stack: set[int] = set()

    def dfs(node: int) -> bool:
        if node in stack:
            return True  # Cycle found
        if node in visited:
            return False

        visited.add(node)
        stack.add(node)

        for dep in deps_map.get(node, []):
            if dfs(dep):
                return True

        stack.remove(node)
        return False

    return dfs(issue_id)


def add_dependency(
    issue_id: int,
    depends_on_id: int,
    tsk_dir: Path | None = None,
) -> None:
    """
    Add a dependency to an issue.

    Args:
        issue_id: The issue that will depend on depends_on_id.
        depends_on_id: The issue that will become a dependency.
        tsk_dir: Path to .tsk/ directory.

    Raises:
        IssueNotFoundError: If either issue doesn't exist.
        DependencyError: If self-reference, duplicate, or would create cycle.
    """
    if tsk_dir is None:
        tsk_dir = find_tsk_dir()

    # Validate self-reference
    if issue_id == depends_on_id:
        raise DependencyError("An issue cannot depend on itself")

    # Validate both issues exist
    issue, status = find_issue(issue_id, tsk_dir)
    find_issue(depends_on_id, tsk_dir)  # Just validate existence

    # Check for duplicate
    if depends_on_id in issue.depends_on:
        raise DependencyError(
            f"Issue {issue_id} already depends on issue {depends_on_id}"
        )

    # Check for cycle
    if has_cycle(issue_id, depends_on_id, tsk_dir):
        raise DependencyError("Adding this dependency would create a cycle")

    # Add the dependency
    all_issues = load_all_issues(tsk_dir)
    updated_issue = replace(
        issue,
        depends_on=issue.depends_on + [depends_on_id],
        updated_at=datetime.now(),
    )

    updated_list = [
        updated_issue if i.id == issue_id else i for i in all_issues[status]
    ]
    save_issues(status, updated_list, tsk_dir)


def remove_dependency(
    issue_id: int,
    depends_on_id: int,
    tsk_dir: Path | None = None,
) -> None:
    """
    Remove a dependency from an issue.

    Args:
        issue_id: The issue to remove the dependency from.
        depends_on_id: The dependency to remove.
        tsk_dir: Path to .tsk/ directory.

    Raises:
        IssueNotFoundError: If issue doesn't exist.
        DependencyError: If the dependency doesn't exist.
    """
    if tsk_dir is None:
        tsk_dir = find_tsk_dir()

    issue, status = find_issue(issue_id, tsk_dir)

    if depends_on_id not in issue.depends_on:
        raise DependencyError(
            f"Issue {issue_id} does not depend on issue {depends_on_id}"
        )

    # Remove the dependency
    all_issues = load_all_issues(tsk_dir)
    new_depends_on = [d for d in issue.depends_on if d != depends_on_id]
    updated_issue = replace(
        issue,
        depends_on=new_depends_on,
        updated_at=datetime.now(),
    )

    updated_list = [
        updated_issue if i.id == issue_id else i for i in all_issues[status]
    ]
    save_issues(status, updated_list, tsk_dir)
