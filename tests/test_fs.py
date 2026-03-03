"""Tests for filesystem utilities."""

from pathlib import Path

import pytest

from tsk.fs import (
    CLOSED_FILE,
    IN_PROGRESS_FILE,
    TODO_FILE,
    TSK_DIR_NAME,
    TskAlreadyExistsError,
    TskNotFoundError,
    find_tsk_dir,
    init_tsk_dir,
)


class TestFindTskDir:
    """Tests for find_tsk_dir function."""

    def test_find_in_current_directory(self, tmp_path: Path) -> None:
        """Test finding .tsk/ in current directory."""
        tsk_dir = tmp_path / TSK_DIR_NAME
        tsk_dir.mkdir()

        result = find_tsk_dir(tmp_path)

        assert result == tsk_dir

    def test_find_in_parent_directory(self, tmp_path: Path) -> None:
        """Test finding .tsk/ in parent directory."""
        tsk_dir = tmp_path / TSK_DIR_NAME
        tsk_dir.mkdir()

        child_dir = tmp_path / "subdir" / "nested"
        child_dir.mkdir(parents=True)

        result = find_tsk_dir(child_dir)

        assert result == tsk_dir

    def test_find_in_grandparent_directory(self, tmp_path: Path) -> None:
        """Test finding .tsk/ multiple levels up."""
        tsk_dir = tmp_path / TSK_DIR_NAME
        tsk_dir.mkdir()

        deep_dir = tmp_path / "a" / "b" / "c" / "d"
        deep_dir.mkdir(parents=True)

        result = find_tsk_dir(deep_dir)

        assert result == tsk_dir

    def test_not_found_raises_error(self, tmp_path: Path) -> None:
        """Test that missing .tsk/ raises TskNotFoundError."""
        with pytest.raises(TskNotFoundError, match="No .tsk/ directory found"):
            find_tsk_dir(tmp_path)

    def test_error_message_suggests_init(self, tmp_path: Path) -> None:
        """Test that error message suggests running tsk init."""
        with pytest.raises(TskNotFoundError, match="tsk init"):
            find_tsk_dir(tmp_path)

    def test_file_not_dir_not_found(self, tmp_path: Path) -> None:
        """Test that a .tsk file (not directory) is not found."""
        tsk_file = tmp_path / TSK_DIR_NAME
        tsk_file.touch()  # Create file, not directory

        with pytest.raises(TskNotFoundError):
            find_tsk_dir(tmp_path)

    def test_finds_closest_tsk_dir(self, tmp_path: Path) -> None:
        """Test that the closest .tsk/ directory is found."""
        # Create .tsk/ in root
        root_tsk = tmp_path / TSK_DIR_NAME
        root_tsk.mkdir()

        # Create nested dir with its own .tsk/
        nested = tmp_path / "project"
        nested.mkdir()
        nested_tsk = nested / TSK_DIR_NAME
        nested_tsk.mkdir()

        # Should find nested .tsk/, not root
        result = find_tsk_dir(nested)
        assert result == nested_tsk

        # But from deeper inside nested, should still find nested
        deep = nested / "src" / "module"
        deep.mkdir(parents=True)
        result = find_tsk_dir(deep)
        assert result == nested_tsk


class TestInitTskDir:
    """Tests for init_tsk_dir function."""

    def test_creates_tsk_directory(self, tmp_path: Path) -> None:
        """Test that init creates .tsk/ directory."""
        result = init_tsk_dir(tmp_path)

        assert result == tmp_path / TSK_DIR_NAME
        assert result.is_dir()

    def test_creates_status_files(self, tmp_path: Path) -> None:
        """Test that init creates all status files."""
        init_tsk_dir(tmp_path)
        tsk_dir = tmp_path / TSK_DIR_NAME

        assert (tsk_dir / TODO_FILE).exists()
        assert (tsk_dir / IN_PROGRESS_FILE).exists()
        assert (tsk_dir / CLOSED_FILE).exists()

    def test_status_files_are_empty(self, tmp_path: Path) -> None:
        """Test that status files are created empty."""
        init_tsk_dir(tmp_path)
        tsk_dir = tmp_path / TSK_DIR_NAME

        assert (tsk_dir / TODO_FILE).read_text() == ""
        assert (tsk_dir / IN_PROGRESS_FILE).read_text() == ""
        assert (tsk_dir / CLOSED_FILE).read_text() == ""

    def test_already_exists_raises_error(self, tmp_path: Path) -> None:
        """Test that init raises error if .tsk/ already exists."""
        (tmp_path / TSK_DIR_NAME).mkdir()

        with pytest.raises(TskAlreadyExistsError, match="already exists"):
            init_tsk_dir(tmp_path)

    def test_returns_tsk_path(self, tmp_path: Path) -> None:
        """Test that init returns path to created .tsk/."""
        result = init_tsk_dir(tmp_path)

        assert result == tmp_path / TSK_DIR_NAME
