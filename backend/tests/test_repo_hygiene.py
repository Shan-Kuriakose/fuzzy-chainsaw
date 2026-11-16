import posixpath
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

ENV_FILES_TO_IGNORE = (".env", ".env.local", ".env.staging")
ENV_FILE_NAME = ".env"
ENV_FILE_EXEMPTION = ".env.example"


def is_environment_file(filename):
    basename = posixpath.basename(filename)
    if basename == ENV_FILE_EXEMPTION:
        return False
    return basename == ENV_FILE_NAME or basename.startswith(f"{ENV_FILE_NAME}.")


def tracked_files():
    git_ls_files = subprocess.run(
        ["git", "ls-files"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return git_ls_files.stdout.splitlines()


def test_env_files_are_ignored_by_git():
    for env_file in ENV_FILES_TO_IGNORE:
        check_ignore = subprocess.run(
            ["git", "check-ignore", "-q", env_file],
            cwd=REPOSITORY_ROOT,
        )

        assert check_ignore.returncode == 0, (
            f"{env_file} is not covered by .gitignore; "
            "secrets must never be committable to source control"
        )


def test_no_environment_file_is_committed_to_source_control():
    committed_environment_files = [
        name for name in tracked_files() if is_environment_file(name)
    ]

    assert committed_environment_files == [], (
        f"{committed_environment_files} is committed to source control; "
        "environment configuration and secrets never travel in the repository"
    )
