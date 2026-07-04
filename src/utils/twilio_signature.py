from fastapi import HTTPException, Request
from twilio.request_validator import RequestValidator

from ..config import get_settings


async def verify_twilio_signature(request: Request) -> None:
    settings = get_settings()
    validator = RequestValidator(settings.twilio_auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    form = await request.form()
    params = dict(form)
    # Reconstruct the URL Twilio actually signed from the known public address,
    # rather than trusting request.url — behind ngrok/a proxy, Starlette often
    # reports the internal http:// scheme/host, which would never match.
    url = f"{settings.server_address.rstrip('/')}{request.url.path}"
    if not validator.validate(url, params, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
