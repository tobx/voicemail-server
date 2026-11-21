import re


def sanitize_single_line(value: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f-\x9f ]+", " ", str(value)).strip()
