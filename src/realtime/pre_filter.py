import re

SKIP_PATTERNS = [
    r"^(да|нет|ок|спс|👍|😂)$",
    r"^@\w+$",
    r"^\+$",
]


def should_buffer(text: str) -> bool:
    """Cheap local filter that discards obvious noise before it enters the buffer.

    Intentionally conservative — only rejects messages that are unambiguously
    not useful. All borderline decisions are left to the AI importance filter.
    """
    if len(text) < 3:
        return False
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return False
    return True
