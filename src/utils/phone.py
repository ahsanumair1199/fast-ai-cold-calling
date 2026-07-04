import phonenumbers
from fastapi import HTTPException


def to_e164(raw: str, default_region: str = "US") -> str:
    try:
        parsed = phonenumbers.parse(raw, default_region)
    except phonenumbers.NumberParseException:
        raise HTTPException(status_code=422, detail=f"Invalid phone number: {raw}")
    if not phonenumbers.is_valid_number(parsed):
        raise HTTPException(status_code=422, detail=f"Invalid phone number: {raw}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
