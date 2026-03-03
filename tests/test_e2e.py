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

    def test_workflow_command(self, e2e_dir: Path) -> None:
        """Test workflow command shows guidance and best practices."""
        result = run_tsk(["workflow"], e2e_dir)
        assert result.returncode == 0
        assert "WORKFLOW" in result.stdout
        assert "BEST PRACTICES" in result.stdout


class TestCLIErrorPaths:
    """Tests for CLI error handling."""

    def test_create_invalid_priority_out_of_range(self, e2e_dir: Path) -> None:
        """Priority must be 0, 1, or 2."""
        run_tsk(["init"], e2e_dir)
        result = run_tsk(["create", "Test", "--priority=5"], e2e_dir)
        assert result.returncode != 0

    def test_create_invalid_priority_negative(self, e2e_dir: Path) -> None:
        """Negative priority is invalid."""
        run_tsk(["init"], e2e_dir)
        result = run_tsk(["create", "Test", "--priority=-1"], e2e_dir)
        assert result.returncode != 0

    def test_create_invalid_priority_non_numeric(self, e2e_dir: Path) -> None:
        """Non-numeric priority is invalid."""
        run_tsk(["init"], e2e_dir)
        result = run_tsk(["create", "Test", "--priority=high"], e2e_dir)
        assert result.returncode != 0

    def test_update_invalid_status(self, e2e_dir: Path) -> None:
        """Invalid status value should fail."""
        run_tsk(["init"], e2e_dir)
        run_tsk(["create", "Test"], e2e_dir)
        result = run_tsk(["update", "1", "--status=invalid"], e2e_dir)
        assert result.returncode != 0

    def test_list_invalid_status_filter(self, e2e_dir: Path) -> None:
        """Invalid status filter should fail."""
        run_tsk(["init"], e2e_dir)
        result = run_tsk(["list", "--status=invalid"], e2e_dir)
        assert result.returncode != 0


class TestEdgeCases:
    """Tests for boundary conditions and edge cases."""

    def test_create_very_long_title(self, e2e_dir: Path) -> None:
        """Very long title should be handled."""
        run_tsk(["init"], e2e_dir)
        long_title = "A" * 500
        result = run_tsk(["create", long_title], e2e_dir)
        assert result.returncode == 0
        result = run_tsk(["show", "1"], e2e_dir)
        assert long_title in result.stdout

    def test_create_very_long_description(self, e2e_dir: Path) -> None:
        """Very long description should be handled."""
        run_tsk(["init"], e2e_dir)
        long_desc = "B" * 2000
        result = run_tsk(["create", "Test", f"--description={long_desc}"], e2e_dir)
        assert result.returncode == 0
        result = run_tsk(["show", "1"], e2e_dir)
        assert long_desc in result.stdout

    def test_create_multiline_description(self, e2e_dir: Path) -> None:
        """Multiline descriptions should be preserved."""
        run_tsk(["init"], e2e_dir)
        desc = "Line 1\nLine 2\nLine 3"
        result = run_tsk(["create", "Test", f"--description={desc}"], e2e_dir)
        assert result.returncode == 0


class TestConcurrentAccess:
    """Tests for concurrent access scenarios."""

    def test_concurrent_creates(self, e2e_dir: Path) -> None:
        """Multiple concurrent creates should assign unique IDs."""
        from concurrent.futures import ThreadPoolExecutor

        run_tsk(["init"], e2e_dir)

        def create_issue(i: int) -> subprocess.CompletedProcess[str]:
            return run_tsk(["create", f"Issue {i}"], e2e_dir)

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(create_issue, range(5)))

        # All should succeed
        assert all(r.returncode == 0 for r in results)

        # Verify 5 unique issues exist
        result = run_tsk(["list"], e2e_dir)
        for i in range(5):
            assert f"Issue {i}" in result.stdout
