"""AC2: unsupported attributes and out-of-range or out-of-enum values are rejected."""


def test_unknown_attribute_name_is_rejected(unsupported_attribute_name):
    import pytest

    from pacca.demographics import (
        DemographicGenerationRequest,
        UnsupportedAttributeError,
        default_registry,
    )

    with pytest.raises(UnsupportedAttributeError, match=unsupported_attribute_name):
        DemographicGenerationRequest.submit(
            attributes={unsupported_attribute_name: "pavlova"},
            registry=default_registry,
        )


def test_age_out_of_range_is_rejected(out_of_range_age):
    import pytest

    from pacca.demographics import (
        AttributeValueError,
        DemographicGenerationRequest,
        default_registry,
    )

    with pytest.raises(AttributeValueError, match=r"\bage\b"):
        DemographicGenerationRequest.submit(
            attributes={"age": out_of_range_age},
            registry=default_registry,
        )


def test_gender_outside_enum_is_rejected(unlisted_gender_value):
    import pytest

    from pacca.demographics import (
        AttributeValueError,
        DemographicGenerationRequest,
        default_registry,
    )

    with pytest.raises(AttributeValueError, match=r"\bgender\b"):
        DemographicGenerationRequest.submit(
            attributes={"gender": unlisted_gender_value},
            registry=default_registry,
        )
