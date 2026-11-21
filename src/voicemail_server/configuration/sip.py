from dataclasses import dataclass
from typing import ClassVar

from .section import Section


@dataclass(frozen=True)
class Sip(Section):
    _ENV_OVERRIDABLE_KEYS: ClassVar[tuple[str, ...]] = ("account", "password")

    account: str
    password: str
    domain: str
    proxy: str
    port: int
    event_timeout: int
    log_level: int
    console_log_level: int
    include_sip_log_messages: bool

    def validate(self) -> None:
        self.validate_string_attributes(
            ["account", "password", "domain"], ["nonempty", "single-line"]
        )
        self.validate_string_attributes(["proxy"], ["single-line"])
        self.validate_number_attribute_ranges(
            [
                ("port", 1, 65_535),
                ("event_timeout", 1, 1_000),
            ]
        )
        self.validate_number_attribute_ranges(
            [
                ("log_level", 0, 6),
                ("console_log_level", 0, 6),
            ]
        )
