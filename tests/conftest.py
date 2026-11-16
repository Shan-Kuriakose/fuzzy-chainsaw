import pytest


@pytest.fixture
def valid_attributes():
    return {
        "age": 34,
        "gender": "female",
        "geography": "CA",
        "income": 52_000,
    }


@pytest.fixture
def unsupported_attribute_name():
    return "favorite_dessert"


@pytest.fixture
def out_of_range_age():
    return 400


@pytest.fixture
def unlisted_gender_value():
    return "shark"
