"""tsk - Issue tracker for LLM agents."""

from dataclasses import replace
from datetime import datetime
from typing import Annotated

import typer

from tsk.fs import TskAlreadyExistsError, TskNotFoundError, init_tsk_dir
from tsk.models import PRIORITY_DEFAULT, Issue, Status
from tsk.storage import (
    DependencyError,
    IssueNotFoundError,
    add_dependency,
    find_issue,
    get_next_id,
    load_all_issues,
    move_issue,
    remove_dependency,
    save_issues,
)

app = typer.Typer(
    name="tsk",
    help="Issue tracker optimized for LLM agents. Tasks are stored in Markdown files.",
    no_args_is_help=True,
)


def _handle_tsk_not_found() -> None:
    """Handle TskNotFoundError consistently."""
    typer.echo("Error: No .tsk/ directory found", err=True)
    typer.echo("Hint: Run 'tsk init' to create one", err=True)
    raise typer.Exit(1) from None


def version_callback(value: bool) -> None:
    if value:
        typer.echo("tsk version 0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
) -> None:
    """Issue tracker optimized for LLM agents."""
    pass


@app.command()
def init() -> None:
    """Initialize a new .tsk/ directory."""
    try:
        init_tsk_dir()
    except TskAlreadyExistsError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None


@app.command()
def create(
    title: str = typer.Argument(..., help="Issue title"),
    description: str = typer.Option(
        "", "--description", "-d", help="Issue description"
    ),
    priority: int = typer.Option(
        PRIORITY_DEFAULT, "--priority", "-p", help="0=critical, 1=medium, 2=low"
    ),
) -> None:
    """Create a new issue."""
    try:
        # Validate priority
        if priority not in (0, 1, 2):
            typer.echo(
                f"Error: Invalid priority {priority}. Must be 0, 1, or 2.", err=True
            )
            raise typer.Exit(1) from None

        issue_id = get_next_id()
        now = datetime.now()

        issue = Issue(
            id=issue_id,
            title=title,
            status=Status.TODO,
            priority=priority,
            description=description,
            created_at=now,
            updated_at=now,
        )

        all_issues = load_all_issues()
        todo_issues = all_issues[Status.TODO]
        todo_issues.append(issue)
        save_issues(Status.TODO, todo_issues)

    except TskNotFoundError:
        _handle_tsk_not_found()


def _format_issue_line(issue: Issue) -> str:
    """Format an issue as a compact single line."""
    return f"#{issue.id} [P{issue.priority}] {issue.title}"


def _sort_issues(issues: list[Issue]) -> list[Issue]:
    """Sort issues by priority (ascending) then ID (ascending)."""
    return sorted(issues, key=lambda i: (i.priority, i.id))


@app.command("list")
def list_issues(
    status: str | None = typer.Option(
        None, "--status", "-s", help="Filter: todo, in_progress, closed, open"
    ),
) -> None:
    """List issues, optionally filtered by status."""
    try:
        all_issues = load_all_issues()

        # Determine which issues to show
        issues_to_show: list[Issue] = []

        if status is None:
            # Show all
            for issue_list in all_issues.values():
                issues_to_show.extend(issue_list)
        elif status == "open":
            # open = todo + in_progress
            issues_to_show.extend(all_issues[Status.TODO])
            issues_to_show.extend(all_issues[Status.IN_PROGRESS])
        elif status == "todo":
            issues_to_show = all_issues[Status.TODO]
        elif status == "in_progress":
            issues_to_show = all_issues[Status.IN_PROGRESS]
        elif status == "closed":
            issues_to_show = all_issues[Status.CLOSED]
        else:
            typer.echo(
                f"Error: Invalid status '{status}'. "
                "Use: todo, in_progress, closed, open",
                err=True,
            )
            raise typer.Exit(1) from None

        if not issues_to_show:
            typer.echo("No tasks found")
            return

        # Sort and display
        sorted_issues = _sort_issues(issues_to_show)
        for issue in sorted_issues:
            typer.echo(_format_issue_line(issue))

    except TskNotFoundError:
        _handle_tsk_not_found()


@app.command()
def show(issue_id: int = typer.Argument(..., help="Issue ID to show")) -> None:
    """Show full details of an issue."""
    try:
        issue, status = find_issue(issue_id)

        typer.echo(f"Issue #{issue.id}")
        typer.echo(f"Title: {issue.title}")
        typer.echo(f"Status: {status.value}")
        typer.echo(f"Priority: P{issue.priority}")

        if issue.depends_on:
            typer.echo("\nDependencies:")
            for dep_id in issue.depends_on:
                try:
                    dep_issue, dep_status = find_issue(dep_id)
                    typer.echo(f"  #{dep_id} [{dep_status.value}] {dep_issue.title}")
                except IssueNotFoundError:
                    typer.echo(f"  #{dep_id} [NOT FOUND]")

        # Find reverse dependencies (issues blocked by this one)
        all_issues = load_all_issues()
        blocked_by_this = [
            (other, st)
            for st, issues in all_issues.items()
            for other in issues
            if issue_id in other.depends_on
        ]
        if blocked_by_this:
            typer.echo("\nBlocked by this:")
            for dep, st in blocked_by_this:
                typer.echo(f"  #{dep.id} [{st.value}] {dep.title}")

        if issue.description:
            typer.echo(f"\nDescription:\n{issue.description}")

        typer.echo(f"\nCreated: {issue.created_at.isoformat()}")
        typer.echo(f"Updated: {issue.updated_at.isoformat()}")
        if issue.closed_at:
            typer.echo(f"Closed: {issue.closed_at.isoformat()}")

    except IssueNotFoundError:
        typer.echo(f"Error: Issue {issue_id} not found", err=True)
        typer.echo("Hint: Run 'tsk list' to see all issues", err=True)
        raise typer.Exit(1) from None
    except TskNotFoundError:
        _handle_tsk_not_found()


def _parse_status(status_str: str) -> Status:
    """Parse status string to Status enum."""
    status_map = {
        "todo": Status.TODO,
        "in_progress": Status.IN_PROGRESS,
        "closed": Status.CLOSED,
    }
    if status_str not in status_map:
        raise ValueError(f"Invalid status: {status_str}")
    return status_map[status_str]


@app.command()
def update(
    issue_id: int = typer.Argument(..., help="Issue ID to update"),
    status: str | None = typer.Option(
        None, "--status", "-s", help="New status: todo, in_progress, closed"
    ),
    priority: int | None = typer.Option(None, "--priority", "-p", help="New priority"),
    title: str | None = typer.Option(None, "--title", "-t", help="New title"),
    description: str | None = typer.Option(
        None, "--description", "-d", help="New description"
    ),
) -> None:
    """Update an existing issue."""
    try:
        issue, current_status = find_issue(issue_id)
        all_issues = load_all_issues()

        # Update fields
        updated_issue = issue

        if title is not None:
            updated_issue = replace(updated_issue, title=title)

        if priority is not None:
            if priority not in (0, 1, 2):
                typer.echo(
                    f"Error: Invalid priority {priority}. Must be 0, 1, or 2.",
                    err=True,
                )
                raise typer.Exit(1) from None
            updated_issue = replace(updated_issue, priority=priority)

        if description is not None:
            updated_issue = replace(updated_issue, description=description)

        # Update timestamp
        updated_issue = replace(updated_issue, updated_at=datetime.now())

        # Handle status change
        if status is not None:
            try:
                new_status = _parse_status(status)
            except ValueError:
                typer.echo(
                    f"Error: Invalid status '{status}'. "
                    "Use: todo, in_progress, closed",
                    err=True,
                )
                raise typer.Exit(1) from None

            if new_status != current_status:
                # Remove from current file
                current_issues = [
                    i for i in all_issues[current_status] if i.id != issue_id
                ]
                save_issues(current_status, current_issues)

                # Update status and closed_at
                updated_issue = replace(updated_issue, status=new_status)
                if new_status == Status.CLOSED and updated_issue.closed_at is None:
                    updated_issue = replace(updated_issue, closed_at=datetime.now())
                elif new_status != Status.CLOSED:
                    updated_issue = replace(updated_issue, closed_at=None)

                # Add to new file
                all_issues[new_status].append(updated_issue)
                save_issues(new_status, all_issues[new_status])
                return

        # No status change - update in place
        updated_list = [
            updated_issue if i.id == issue_id else i for i in all_issues[current_status]
        ]
        save_issues(current_status, updated_list)

    except IssueNotFoundError:
        typer.echo(f"Error: Issue {issue_id} not found", err=True)
        typer.echo("Hint: Run 'tsk list' to see all issues", err=True)
        raise typer.Exit(1) from None
    except TskNotFoundError:
        _handle_tsk_not_found()


@app.command()
def close(
    issue_ids: Annotated[list[int], typer.Argument(help="Issue ID(s) to close")],
) -> None:
    """Close one or more issues."""
    try:
        errors: list[str] = []

        for issue_id in issue_ids:
            try:
                move_issue(issue_id, Status.CLOSED)
            except IssueNotFoundError:
                errors.append(f"Issue {issue_id} not found")

        # Report errors
        for error in errors:
            typer.echo(f"Error: {error}", err=True)

        if errors:
            typer.echo("Hint: Run 'tsk list' to see all issues", err=True)
            raise typer.Exit(1) from None

    except TskNotFoundError:
        _handle_tsk_not_found()


WORKFLOW_TEXT = """
tsk - Issue Tracker for LLM Agents

WORKFLOW:
  1. Create issues: tsk create "title" [--priority=0|1|2] [--description="..."]
  2. View ready work: tsk ready
  3. Work on issue: tsk update <id> --status=in_progress
  4. Complete issue: tsk close <id>

COMMANDS:
  tsk create                  Create a new issue
  tsk list [--status=...]     List issues (todo|in_progress|closed|open)
  tsk ready                   Show unblocked issues ready to work on
  tsk show <id>               Show full issue details
  tsk update <id> [options]   Update issue fields or status
  tsk close <id> [<id>...]    Close one or more issues

  tsk dep add <id> <dep-id>   Add dependency: id depends on dep-id
  tsk dep remove <id> <dep-id> Remove a dependency

PRIORITIES:
  0 = Critical (highest)
  1 = Medium (default)
  2 = Low

STATUS VALUES:
  todo        - New issues
  in_progress - Work started
  closed      - Completed
  open        - todo + in_progress (for filtering)

BEST PRACTICES FOR LLM AGENTS:
  - Use 'tsk ready' to find next task (respects dependencies)
  - Set issue to in_progress before starting work
  - Close issues when done to unblock dependent tasks
  - Use dependencies to enforce task ordering
""".strip()


@app.command("workflow")
def workflow_command() -> None:
    """Show workflow guidance and best practices."""
    typer.echo(WORKFLOW_TEXT)


def _is_blocked(issue: Issue, all_issues: dict[Status, list[Issue]]) -> bool:
    """Check if an issue is blocked by any unclosed dependencies."""
    closed_ids = {i.id for i in all_issues[Status.CLOSED]}
    return any(dep_id not in closed_ids for dep_id in issue.depends_on)


@app.command()
def ready() -> None:
    """Show unblocked issues ready to work on."""
    try:
        all_issues = load_all_issues()

        # Get open issues (todo + in_progress)
        open_issues = all_issues[Status.TODO] + all_issues[Status.IN_PROGRESS]

        # Filter to unblocked
        ready_issues = [i for i in open_issues if not _is_blocked(i, all_issues)]

        if not ready_issues:
            typer.echo("No tasks found")
            return

        # Sort and display
        sorted_issues = _sort_issues(ready_issues)
        for issue in sorted_issues:
            typer.echo(_format_issue_line(issue))

    except TskNotFoundError:
        _handle_tsk_not_found()


# Dependency subcommands
dep_app = typer.Typer(help="Manage issue dependencies")
app.add_typer(dep_app, name="dep")


@dep_app.command("add")
def dep_add(
    issue_id: int = typer.Argument(..., help="Issue ID"),
    depends_on_id: int = typer.Argument(..., help="ID of issue it depends on"),
) -> None:
    """Add a dependency: issue depends on depends-on."""
    try:
        add_dependency(issue_id, depends_on_id)
    except IssueNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        typer.echo("Hint: Run 'tsk list' to see all issues", err=True)
        raise typer.Exit(1) from None
    except DependencyError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None
    except TskNotFoundError:
        _handle_tsk_not_found()


@dep_app.command("remove")
def dep_remove(
    issue_id: int = typer.Argument(..., help="Issue ID"),
    depends_on_id: int = typer.Argument(..., help="ID of dependency to remove"),
) -> None:
    """Remove a dependency from an issue."""
    try:
        remove_dependency(issue_id, depends_on_id)
    except IssueNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        typer.echo("Hint: Run 'tsk list' to see all issues", err=True)
        raise typer.Exit(1) from None
    except DependencyError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None
    except TskNotFoundError:
        _handle_tsk_not_found()


if __name__ == "__main__":
    app()
