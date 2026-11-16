from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"


def test_merge_to_main_builds_tests_and_deploys_to_staging():
    assert CI_WORKFLOW.exists(), (
        "No CI workflow; a merge to main is not built, tested or deployed to staging"
    )

    workflow = CI_WORKFLOW.read_text().lower()

    assert "main" in workflow, "CI does not run on merges to main"
    assert "pytest" in workflow, "CI does not run the backend test suite"
    assert "coverage" in workflow, "CI does not enforce the coverage gate"
    assert "deploy" in workflow, "CI does not deploy the app skeleton"
    assert "staging" in workflow, "CI does not deploy to a staging environment"


def test_ci_smoke_checks_the_staging_root_url_after_deploy():
    assert CI_WORKFLOW.exists(), (
        "No CI workflow; there is no post-deploy smoke check of the staging root URL"
    )

    workflow = CI_WORKFLOW.read_text().lower()

    assert "smoke" in workflow, "CI lacks a post-deploy smoke check step"
    assert "200" in workflow, "Smoke check does not assert a successful (200) response"
