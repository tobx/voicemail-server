from typing import TypedDict

from .types import Language


class Template(TypedDict):
    months: tuple[str, str, str, str, str, str, str, str, str, str, str, str]
    subject: str
    greeting: str
    info: str
    message: str
    details: str
    signature: str


_DEFAULT_TEMPLATE: Template = {
    "months": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "subject": "📲 {caller}",
    "greeting": "Hello {recipient},",
    "info": "{caller} called on {month} {day} at {time}.",
    "message": "A voicemail was left and is attached.",
    "details": "Details: {note}",
    "signature": "Your Voicemail Server",
}


TEMPLATES: dict[Language, Template] = {
    "english": _DEFAULT_TEMPLATE,
    "german": {
        **_DEFAULT_TEMPLATE,
        "months": (
            "Januar",
            "Februar",
            "März",
            "April",
            "Mai",
            "Juni",
            "Juli",
            "August",
            "September",
            "Oktober",
            "November",
            "Dezember",
        ),
        "greeting": "Hallo {recipient},",
        "info": "{caller} hat am {day}. {month} um {time} angerufen.",
        "message": "Eine Sprachnachricht wurde hinterlassen und ist angehängt.",
        "signature": "Dein Voicemail Server",
    },
}
