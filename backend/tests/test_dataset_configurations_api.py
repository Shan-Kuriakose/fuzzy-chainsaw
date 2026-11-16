"""Acceptance tests for saving, sharing and reusing dataset configurations.

Each test maps to an acceptance criterion of the story:
AC1 - a configured dataset is saved under a name and retrieved later;
      duplicates within a team and unsaved names are refused
AC2 - reproducing a saved configuration regenerates the identical dataset
      the engine would draw from the same seed and parameters
AC3 - a configuration saved into a team is listable and reproducible by
      others acting within that team's scope, and invisible from other teams
AC4 - rerunning a saved configuration returns the exact records it first
      produced, so a defect can be handed off unchanged
"""

ATLAS_TEAM = "atlas"
HELIOS_TEAM = "helios"

SAVED_NAME = "atlas-baseline"
SAVED_COUNT = 10
SAVED_SEED = 42
SAVED_CONFIGURATION = {
    "age_range": [25, 45],
    "genders": ["Female", "Male"],
    "geographies": ["Region North"],
    "income_range": [30_000, 90_000],
}


def _saved_configuration_payload(**overrides):
    payload = {
        "name": SAVED_NAME,
        "count": SAVED_COUNT,
        "seed": SAVED_SEED,
        "configuration": SAVED_CONFIGURATION,
    }
    payload.update(overrides)
    return payload


def _client_over(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import Settings

    forbidden_values_path = tmp_path / "forbidden-values.json"
    forbidden_values_path.write_text("[]", encoding="utf-8")
    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'dataset-configurations.db'}",
        forbidden_values_path=forbidden_values_path,
    )
    return TestClient(create_app(settings=settings))


def _save_configuration(client, **overrides):
    return client.put(
        f"/api/teams/{overrides.get('team', ATLAS_TEAM)}/dataset-configurations",
        json=_saved_configuration_payload(
            **{key: value for key, value in overrides.items() if key != "team"}
        ),
    )


def _dataset_rows(configuration_payload, count, seed):
    from persona_engine import GenerationConfig, PersonaGenerator

    dataset = PersonaGenerator().generate_dataset(
        GenerationConfig.from_payload(configuration_payload),
        count=count,
        seed=seed,
    )
    return [persona.to_payload() for persona in dataset.personas]


def test_saving_a_configuration_stores_it_under_its_name_for_later_retrieval(tmp_path):
    client = _client_over(tmp_path)

    save_response = _save_configuration(client)

    assert save_response.status_code == 201, save_response.text
    retrieval_response = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}"
    )
    assert retrieval_response.status_code == 200, retrieval_response.text
    retrieved = retrieval_response.json()
    assert retrieved["name"] == SAVED_NAME
    assert retrieved["team"] == ATLAS_TEAM
    assert retrieved["seed"] == SAVED_SEED
    assert retrieved["count"] == SAVED_COUNT
    assert retrieved["configuration"] == SAVED_CONFIGURATION


def test_saving_a_duplicate_name_within_a_team_is_refused(tmp_path):
    client = _client_over(tmp_path)

    first_save = _save_configuration(client)
    assert first_save.status_code == 201, first_save.text

    second_save = _save_configuration(client, seed=SAVED_SEED + 1)

    assert second_save.status_code == 409, second_save.text
    stored = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}"
    ).json()
    assert stored["seed"] == SAVED_SEED, "the refused save overwrote the stored one"


def test_getting_an_unsaved_configuration_is_refused(tmp_path):
    client = _client_over(tmp_path)
    setup_save = _save_configuration(client, name="atlas-smoke-suite")
    assert setup_save.status_code == 201, setup_save.text

    retrieval_response = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}"
    )
    reproduce_response = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}/reproduce"
    )

    assert retrieval_response.status_code == 404, retrieval_response.text
    assert reproduce_response.status_code == 404, reproduce_response.text


def test_reproducing_a_saved_configuration_regenerates_the_identical_dataset(tmp_path):
    client = _client_over(tmp_path)
    save_response = _save_configuration(client)
    assert save_response.status_code == 201, save_response.text

    reproduction = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}/reproduce"
    )

    assert reproduction.status_code == 200, reproduction.text
    reproduced = reproduction.json()
    assert reproduced["seed"] == SAVED_SEED
    assert reproduced["count"] == SAVED_COUNT
    expected_rows = _dataset_rows(SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)
    assert reproduced["personas"] == expected_rows


def test_a_configuration_saved_into_a_team_is_listed_for_that_team(tmp_path):
    client = _client_over(tmp_path)
    _save_configuration(client)
    _save_configuration(client, name="atlas-smoke-suite")

    listing_response = client.get(f"/api/teams/{ATLAS_TEAM}/dataset-configurations")

    assert listing_response.status_code == 200, listing_response.text
    listed_names = [entry["name"] for entry in listing_response.json()]
    assert SAVED_NAME in listed_names
    assert "atlas-smoke-suite" in listed_names


def test_another_member_of_the_team_can_reproduce_a_shared_configuration(tmp_path):
    author_client = _client_over(tmp_path)
    _save_configuration(author_client)

    teammate_client = _client_over(tmp_path)
    roster_response = teammate_client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations"
    )
    assert roster_response.status_code == 200, roster_response.text
    assert SAVED_NAME in [entry["name"] for entry in roster_response.json()]

    reproduction = teammate_client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}/reproduce"
    )

    assert reproduction.status_code == 200, reproduction.text
    reproduced = reproduction.json()
    expected_rows = _dataset_rows(SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)
    assert reproduced["personas"] == expected_rows


def test_a_configuration_in_one_team_is_not_listed_from_another_team(tmp_path):
    client = _client_over(tmp_path)
    _save_configuration(client)

    other_team_listing = client.get(f"/api/teams/{HELIOS_TEAM}/dataset-configurations")
    other_team_retrieval = client.get(
        f"/api/teams/{HELIOS_TEAM}/dataset-configurations/{SAVED_NAME}"
    )

    assert other_team_listing.status_code == 200, other_team_listing.text
    listed_names = [entry["name"] for entry in other_team_listing.json()]
    assert SAVED_NAME not in listed_names
    assert other_team_retrieval.status_code == 404, other_team_retrieval.text


def test_reproduce_returns_the_exact_saved_records_after_a_failure_was_surfaced(
    tmp_path,
):
    client = _client_over(tmp_path)
    _save_configuration(client)
    _save_configuration(client, name="atlas-later-suite", seed=208, count=7)

    first_hand_off = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}/reproduce"
    )
    assert first_hand_off.status_code == 200, first_hand_off.text
    _save_configuration(client, name="atlas-one-more", seed=11, count=4)

    rerun_hand_off = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}/reproduce"
    )

    assert rerun_hand_off.status_code == 200, rerun_hand_off.text
    assert rerun_hand_off.json() == first_hand_off.json()
    assert len(rerun_hand_off.json()["personas"]) == SAVED_COUNT


def test_screenings_endpoint_lists_evidence_per_team(tmp_path):
    client = _client_over(tmp_path)
    save_response = _save_configuration(client)
    assert save_response.status_code == 201, save_response.text

    listing_response = client.get(
        f"/api/teams/{ATLAS_TEAM}/identity-safety-screenings"
    )

    assert listing_response.status_code == 200, listing_response.text
    screenings = listing_response.json()
    assert [entry["name"] for entry in screenings] == [SAVED_NAME]
    assert [entry["passed"] for entry in screenings] == [True]
