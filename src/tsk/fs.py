"""Filesystem utilities for tsk."""

from pathlib import Path

TSK_DIR_NAME = ".tsk"

# Status files in .tsk/ directory
TODO_FILE = "todo.md"
IN_PROGRESS_FILE = "in_progress.md"
CLOSED_FILE = "closed.md"


class TskNotFoundError(Exception):
    """Raised when .tsk/ directory is not found."""

    pass


class TskAlreadyExistsError(Exception):
    """Raised when .tsk/ directory already exists."""

    pass


def find_tsk_dir(start_path: Path | None = None) -> Path:
    """
    Find .tsk/ directory by searching recursively up the directory tree.

    Args:
        start_path: Starting directory for search.
            Defaults to current working directory.

    Returns:
        Path to the .tsk/ directory.

    Raises:
        TskNotFoundError: If .tsk/ directory is not found.
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while True:
        tsk_path = current / TSK_DIR_NAME
        if tsk_path.is_dir():
            return tsk_path

        parent = current.parent
        if parent == current:
            # Reached root directory
            raise TskNotFoundError(
                f"No {TSK_DIR_NAME}/ directory found. Run 'tsk init' to create one."
            )
        current = parent


def init_tsk_dir(target_path: Path | None = None) -> Path:
    """
    Initialize a new .tsk/ directory with empty status files.

    Args:
        target_path: Directory where .tsk/ should be created.
            Defaults to current working directory.

    Returns:
        Path to the created .tsk/ directory.

    Raises:
        TskAlreadyExistsError: If .tsk/ directory already exists.
    """
    if target_path is None:
        target_path = Path.cwd()

    tsk_dir = target_path / TSK_DIR_NAME

    if tsk_dir.exists():
        raise TskAlreadyExistsError(
            f"{TSK_DIR_NAME}/ directory already exists at {tsk_dir}"
        )

    tsk_dir.mkdir()

    # Create empty status files
    for filename in (TODO_FILE, IN_PROGRESS_FILE, CLOSED_FILE):
        (tsk_dir / filename).touch()

    return tsk_dir
