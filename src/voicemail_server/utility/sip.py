import re

from urllib.parse import unquote


def extract_user_from_name_addr(name_address: str) -> str:
    address = re.search(r"<([^>]+)>", name_address)
    uri = address.group(1) if address else name_address.strip()
    match = re.match(r"(?:sips?|tel):([^@;>?\s]+)", uri, flags=re.IGNORECASE)
    return unquote(match.group(1)) if match else ""
