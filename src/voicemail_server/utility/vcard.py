import phonenumbers as pn

from vobject.base import Component
from vobject.vcard import Name


def get_contact_full_name(contact: Component) -> str:
    fn = getattr(contact, "fn", None)
    raw_full_name: object = getattr(fn, "value", None)
    if isinstance(raw_full_name, str):
        full_name = " ".join(raw_full_name.split())
        if full_name:
            return full_name

    n = getattr(contact, "n", None)
    raw_name: object = getattr(n, "value", None)
    if not isinstance(raw_name, Name):
        return ""

    parts: list[str] = []
    for part in (raw_name.given, raw_name.family):
        if isinstance(part, str):
            parts.append(part)
        else:
            parts.extend(part)

    return " ".join(" ".join(parts).split())


def get_contact_phone_numbers(
    contact: Component, default_region_code: str | None
) -> list[str]:
    numbers: list[str] = []
    for tel in contact.contents.get("tel", []):
        raw_value: object = getattr(tel, "value", None)
        if not isinstance(raw_value, str):
            continue

        value = raw_value.strip()
        if value.lower().startswith("tel:"):
            value = value[4:]

        try:
            number = pn.parse(value, default_region_code)
        except pn.NumberParseException:
            continue

        if pn.is_valid_number(number):
            numbers.append(pn.format_number(number, pn.PhoneNumberFormat.E164))

    return numbers
