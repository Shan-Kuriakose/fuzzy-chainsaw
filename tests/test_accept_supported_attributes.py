"""AC1: a generation request naming supported attributes is accepted."""


def test_request_with_age_gender_geography_income_is_accepted(valid_attributes):
    from pacca.demographics import DemographicGenerationRequest, default_registry

    request = DemographicGenerationRequest.submit(
        attributes=valid_attributes, registry=default_registry
    )

    assert request.attributes == valid_attributes
