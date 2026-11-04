import re

_PATTERNS = (
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), "[PAN_REDACTED]"),
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[AADHAAR_REDACTED]"),
    (re.compile(r"\b\d{9,18}\b"), "[ACCOUNT_REDACTED]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL_REDACTED]"),
)


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
