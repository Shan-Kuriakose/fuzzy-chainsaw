from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"

PLACEHOLDER_PAGE = "fuzzy chain saw"


def test_merge_to_main_builds_tests_and_deploys_to_staging():
    assert CI_WORKFLOW.exists(), (
        "No CI workflow; a merge to main is not built, tested or deployed to staging"
    )

    workflow = CI_WORKFLOW.read_text().lower()

    assert "refs/heads/main" in workflow, "CI does not run on a merge to main"
    assert "pytest" in workflow, "CI does not run the backend test suite"
    assert "coverage" in workflow, "CI does not enforce the test coverage gate"
    assert "vitest" in workflow, "CI does not run the frontend test suite"
    assert "docker build" in workflow, "CI does not build the application image"
    assert "staging" in workflow, "CI does not deploy to a staging environment"
    assert "needs: [build]" in workflow, "The deploy does not run after the image build"
    assert "refusing" in workflow, (
        "CI fakes a deploy when the staging configuration is missing"
    )


def test_ci_smoke_checks_the_staging_root_url_after_deploy():
    assert CI_WORKFLOW.exists(), (
        "No CI workflow; there is no post-deploy smoke check of the staging root URL"
    )

    workflow = CI_WORKFLOW.read_text().lower()

    assert "smoke" in workflow, "CI lacks a post-deploy smoke check step"
    assert "curl" in workflow, "The smoke check does not fetch the staging root URL"
    assert "needs: [deploy]" in workflow, "The smoke check does not run after the deploy"
    assert "200" in workflow, "Smoke check does not assert a successful (200) response"
    assert PLACEHOLDER_PAGE in workflow, (
        "The smoke check does not verify the placeholder home page rendered"
    )
