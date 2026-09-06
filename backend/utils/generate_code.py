"""Port of utils/generateCode.js."""
import secrets


def generate_registration_code(prefix: str) -> str:
    """Generates a short, human-friendly, unique-enough registration code.
    Example: RE-STL-8F3K2Q (stall) | RE-VIS-8F3K2Q (visitor)"""
    random_part = secrets.token_hex(4).upper()[:6]
    return f"RE-{prefix}-{random_part}"
