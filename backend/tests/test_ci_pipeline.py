import re
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


def job_block(workflow_text, job_name):
    lines = workflow_text.splitlines()
    for start, line in enumerate(lines):
        if line == f"  {job_name}:":
            break
    else:
        return ""

    for end in range(start + 1, len(lines)):
        following = lines[end]
        if following and not following.startswith("    ") and following.endswith(":"):
            return "\n".join(lines[start:end])
    return "\n".join(lines[start:])


def prerequisites(job_block_text):
    required = []
    for line in job_block_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("needs:"):
            required += re.findall(r"[a-z_]+", stripped.removeprefix("needs:"))
    return set(required)


def test_staging_deployment_waits_for_lint_test_and_build_to_pass():
    workflow = CI_WORKFLOW.read_text()

    build = prerequisites(job_block(workflow, "build"))
    deploy = prerequisites(job_block(workflow, "deploy"))
    smoke = prerequisites(job_block(workflow, "smoke"))

    assert build == {"lint", "test"}, (
        "The image build does not wait for both the lint and the test suites"
    )
    assert deploy == {"build"}, "Staging deploy does not wait for a built image"
    assert smoke == {"deploy"}, "The staging smoke check does not wait for the deploy"


def test_staging_deploy_and_smoke_run_only_on_merges_to_main():
    workflow = CI_WORKFLOW.read_text()

    for job in ("deploy", "smoke"):
        block = job_block(workflow, job)

        assert "refs/heads/main" in block, f"The {job} job is not gated to main"
        assert "event_name == 'push'" in block, (
            f"The {job} job runs on non-merge events that touch main"
        )
