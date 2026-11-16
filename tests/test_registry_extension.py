"""AC3: new demographic attributes extend the schema without core redesign."""


def test_new_attribute_accepted_after_registration():
    import pytest

    from pacca.demographics import (
        DemographicAttributeRegistry,
        DemographicAttributeSpec,
        DemographicGenerationRequest,
        UnsupportedAttributeError,
        default_registry,
    )

    new_spec = DemographicAttributeSpec(
        name="ethnicity",
        kind="enum",
        allowed_values=("hispanic_or_latino", "not_hispanic_or_latino"),
        description="Ethnicity categories for demographic synthesis.",
    )

    with pytest.raises(UnsupportedAttributeError):
        DemographicGenerationRequest.submit(
            attributes={"ethnicity": "not_hispanic_or_latino"},
            registry=default_registry,
        )

    extended = default_registry.with_attribute(new_spec)

    assert isinstance(extended, DemographicAttributeRegistry)

    request = DemographicGenerationRequest.submit(
        attributes={"ethnicity": "not_hispanic_or_latino"},
        registry=extended,
    )

    assert request.attributes == {"ethnicity": "not_hispanic_or_latino"}

    with pytest.raises(UnsupportedAttributeError):
        DemographicGenerationRequest.submit(
            attributes={"ethnicity": "not_hispanic_or_latino"},
            registry=default_registry,
        )


def test_duplicate_attribute_name_is_rejected():
    import pytest

    from pacca.demographics import DemographicAttributeSpec, default_registry

    duplicate = DemographicAttributeSpec(
        name="age",
        kind="range",
        minimum=0,
        maximum=120,
        description="Duplicates the built-in age range.",
    )

    with pytest.raises(ValueError, match=r"\bage\b"):
        default_registry.with_attribute(duplicate)
