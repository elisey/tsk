# tsk

A lightweight issue tracker designed for LLM agents. Issues are stored as Markdown files, making them human-readable and easy to monitor.

## Quick Start

```bash
# Initialize in your project
tsk init

# Create an issue
tsk create "Implement user authentication" --priority=0

# See what's ready to work on
tsk ready

# Start working on an issue
tsk update 1 --status=in_progress

# Complete the issue
tsk close 1
```

## Commands

| Command | Description |
|---------|-------------|
| `tsk init` | Create `.tsk/` directory |
| `tsk create <title>` | Create a new issue |
| `tsk list [--status=...]` | List issues (todo, in_progress, closed, open) |
| `tsk ready` | Show unblocked issues ready to work on |
| `tsk show <id>` | Show full issue details |
| `tsk update <id> [options]` | Update issue fields or status |
| `tsk close <id> [<id>...]` | Close one or more issues |
| `tsk dep add <id> <dep-id>` | Add dependency: id depends on dep-id |
| `tsk dep remove <id> <dep-id>` | Remove a dependency |
| `tsk help` | Show extended help with workflow |

### Create Options

```bash
tsk create "title" [--priority=0|1|2] [--description="..."]
```

### Update Options

```bash
tsk update <id> [--status=...] [--priority=...] [--title=...] [--description=...]
```

## Priority Levels

| Priority | Meaning |
|----------|---------|
| 0 | Critical |
| 1 | Medium (default) |
| 2 | Low |

## Status Values

| Status | Description |
|--------|-------------|
| `todo` | New issues |
| `in_progress` | Work started |
| `closed` | Completed |
| `open` | Filter: todo + in_progress |

## Best Practices for LLM Agents

1. **Start**: Run `tsk ready` to find actionable work
2. **Claim**: Use `tsk update <id> --status=in_progress` before starting
3. **Work**: Implement the task
4. **Complete**: Use `tsk close <id>` when done

Use dependencies to enforce task ordering:

```bash
# Task 2 can't start until task 1 is closed
tsk dep add 2 1
```

## File Structure

```
.tsk/
  todo.md        # Issues not yet started
  in_progress.md # Issues being worked on
  closed.md      # Completed issues
```

All files are Markdown - open them directly to monitor progress.

## Development

```bash
# Install dev dependencies
uv sync --all-groups

# Run tests
task test

# Type checking and linting
task lint

# Format all code
task format

# Run all checks
task ci
```

## License

MIT
