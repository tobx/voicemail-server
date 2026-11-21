import phonenumbers as pn


def format(value: str, region_code: str) -> str | None:
    try:
        number = pn.parse(value, region_code)
        format = pn.PhoneNumberFormat.INTERNATIONAL
        return pn.format_number(number, format)
    except pn.NumberParseException:
        return None
