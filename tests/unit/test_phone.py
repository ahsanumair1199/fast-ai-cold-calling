import pytest
from fastapi import HTTPException

from src.utils.phone import to_e164


def test_valid_us_number_normalizes_to_e164():
    assert to_e164("2015550123") == "+12015550123"


def test_already_e164_passes_through():
    assert to_e164("+12015550123") == "+12015550123"


def test_garbage_input_rejected():
    with pytest.raises(HTTPException) as exc_info:
        to_e164("not-a-number")
    assert exc_info.value.status_code == 422


def test_fake_555_number_rejected_as_invalid():
    # 555-xxxx exchange numbers (outside the 555-0100..0199 reserved block)
    # aren't real assignable lines — the validator should catch this, not just
    # check that the string is digit-shaped.
    with pytest.raises(HTTPException):
        to_e164("5551234567")
