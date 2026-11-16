import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SECRET_FILE_SUFFIXES = (".pem", ".key")
SECRET_FILE_NAMES_PREFIX = "id_rsa"


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def _looks_like_a_secret_file(tracked_path: str) -> bool:
    name = Path(tracked_path).name
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    if name.startswith(SECRET_FILE_NAMES_PREFIX):
        return True
    return name.endswith(SECRET_FILE_SUFFIXES)


def test_no_credential_files_are_tracked_and_gitignore_covers_them():
    tracked_files = _tracked_files()
    offenders = [path for path in tracked_files if _looks_like_a_secret_file(path)]
    assert offenders == [], f"Credential-shaped files are tracked in git: {offenders}"

    gitignore = REPO_ROOT / ".gitignore"
    assert gitignore.is_file(), ".gitignore must exist before the first commit"
    patterns = [
        line.strip()
        for line in gitignore.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert any(".env" in pattern for pattern in patterns), (
        f".gitignore at {gitignore} does not ignore .env files: {patterns}"
    )
