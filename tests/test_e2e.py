"""End-to-end tests for the full workflow."""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def e2e_dir(tmp_path: Path) -> Path:
    """Create a directory for E2E testing."""
    return tmp_path


def run_tsk(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run tsk command and return result."""
    return subprocess.run(
        ["uv", "run", "tsk", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class TestE2EWorkflow:
    """End-to-end workflow tests."""

    def test_full_workflow(self, e2e_dir: Path) -> None:
        """Test complete workflow from init to close."""
        # 1. Init
        result = run_tsk(["init"], e2e_dir)
        assert result.returncode == 0
        assert (e2e_dir / ".tsk" / "todo.md").exists()

        # 2. Create issues
        result = run_tsk(["create", "Task A", "--priority=0"], e2e_dir)
        assert result.returncode == 0

        result = run_tsk(["create", "Task B", "--priority=1"], e2e_dir)
        assert result.returncode == 0

        result = run_tsk(["create", "Task C", "--priority=2"], e2e_dir)
        assert result.returncode == 0

        # 3. List shows all issues
        result = run_tsk(["list"], e2e_dir)
        assert result.returncode == 0
        assert "Task A" in result.stdout
        assert "Task B" in result.stdout
        assert "Task C" in result.stdout

        # 4. Show issue details
        result = run_tsk(["show", "1"], e2e_dir)
        assert result.returncode == 0
        assert "Task A" in result.stdout
        assert "Priority: P0" in result.stdout

        # 5. Add dependency: Task C depends on Task B
        result = run_tsk(["dep", "add", "3", "2"], e2e_dir)
        assert result.returncode == 0

        # 6. Ready should not show blocked tasks
        result = run_tsk(["ready"], e2e_dir)
        assert result.returncode == 0
        assert "Task A" in result.stdout
        assert "Task B" in result.stdout
        assert "Task C" not in result.stdout  # Blocked by Task B

        # 7. Update Task A to in_progress
        result = run_tsk(["update", "1", "--status=in_progress"], e2e_dir)
        assert result.returncode == 0

        # 8. Close Task A
        result = run_tsk(["close", "1"], e2e_dir)
        assert result.returncode == 0

        # 9. Close Task B (will unblock Task C)
        result = run_tsk(["close", "2"], e2e_dir)
        assert result.returncode == 0

        # 10. Ready should now show Task C
        result = run_tsk(["ready"], e2e_dir)
        assert result.returncode == 0
        assert "Task C" in result.stdout

        # 11. Verify closed issues
        result = run_tsk(["list", "--status=closed"], e2e_dir)
        assert result.returncode == 0
        assert "Task A" in result.stdout
        assert "Task B" in result.stdout

    def test_no_init_error(self, e2e_dir: Path) -> None:
        """Test that commands fail gracefully without init."""
        result = run_tsk(["list"], e2e_dir)
        assert result.returncode == 1
        assert "tsk init" in result.stderr

    def test_invalid_issue_error(self, e2e_dir: Path) -> None:
        """Test that invalid issue ID shows helpful error."""
        run_tsk(["init"], e2e_dir)

        result = run_tsk(["show", "99"], e2e_dir)
        assert result.returncode == 1
        assert "not found" in result.stderr
        assert "tsk list" in result.stderr

    def test_help_command(self, e2e_dir: Path) -> None:
        """Test help command shows workflow."""
        result = run_tsk(["help"], e2e_dir)
        assert result.returncode == 0
        assert "WORKFLOW" in result.stdout
        assert "BEST PRACTICES" in result.stdout
