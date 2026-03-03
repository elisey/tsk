## tsk Workflow Integration

This project is an issue tracking. Issues are stored in .tsk/ files as Markdown file. Separate file for each Status.
This Tsk manager is designed to be used by LLM agent to track tasks, add new tasks.
User can monitor task by opening Markdown file in ./tsk dir.
This tool supports only cli interface
Use python, uv. Для парсинга аргументов используй библиотеку Typer


# CLI commands for agents (use these instead)
tsk ready              # Show issues ready to work (no blockers). Ordered by Priority
tsk list --status=open # All open issues
tsk show <id>          # Full issue details with dependencies
tsk create --title="..." --description="..." --priority=2
tsk update <id> --status=in_progress
tsk close <id>
tsk close <id1> <id2>  # Close multiple issues at once
tsk --help.            # Show full guide and workflow to be used by LLM agent. It got injected into LLM context on start. LLM

### Workflow Pattern

1. **Start**: Run `tsk ready` to find actionable work
2. **Claim**: Use `tsk update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Complete**: Use `tsk close <id>`

### Key Concepts

- **Dependencies**: Issues can block other issues. `tsk ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers, not words)
- **Blocking**: `tsk dep add <issue> <depends-on>` to add dependencies
- **Status**: todo, in_progress, closed

### Session Protocol

**Before ending any session, run this checklist:**

```bash
git status              # Check what changed
git add <files>         # Stage code changes
git commit -m "..."     # Commit code
git push                # Push to remote
### Best Practices

- Check tsk ready at session start to find available work
- Update status as you work (todo → in_progress → closed)
- Create new issues with tsk create when you discover tasks
- Use descriptive titles and set appropriate priority
