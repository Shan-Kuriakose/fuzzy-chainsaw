import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

ENV_FILES_TO_IGNORE = (".env", ".env.local", ".env.staging")


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
