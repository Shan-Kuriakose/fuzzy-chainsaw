import re
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

ENV_FILES_TO_IGNORE = (".env", ".env.local", ".env.staging")

HARD_CODED_CREDENTIAL = re.compile(
    r"(?i)\b(api_?key|token|secret|password|passwd)\b"
    r"\s*[=:]\s*[\"'][^\"']{8,}[\"']"
)


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


def test_no_committed_file_carries_a_hard_coded_credential():
    tracked_files = subprocess.run(
        ["git", "ls-files"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.splitlines()

    offenders = []
    for tracked in tracked_files:
        content = (REPOSITORY_ROOT / tracked).read_text(errors="ignore")
        if HARD_CODED_CREDENTIAL.search(content):
            offenders.append(tracked)

    assert offenders == [], (
        "Hard-coded credentials must never be committed; resolve them from the "
        f"environment instead of committing {offenders}"
    )
