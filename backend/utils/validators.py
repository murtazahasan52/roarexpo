"""Small shared validators, standing in for the express-validator chains the
old routes used (isEmail / isURL / etc.) — kept lightweight since the React
frontend already does its own pre-submit validation and only ever displays
`message` from an error response, never the `errors` array (see
StallRegistration.jsx / VisitorRegistration.jsx). The array is still built
for parity/debugging."""
import re
from email_validator import validate_email, EmailNotValidError

_URL_RE = re.compile(r"^(https?://)?[a-zA-Z0-9](?:[a-zA-Z0-9\-._~%]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}(:\d+)?(/\S*)?$")


def is_valid_email(value: str) -> bool:
    if not value:
        return False
    try:
        validate_email(value, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def is_valid_url(value: str) -> bool:
    if not value:
        return False
    return bool(_URL_RE.match(value.strip()))
