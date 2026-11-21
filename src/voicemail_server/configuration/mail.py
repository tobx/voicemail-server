import phonenumbers
import shutil

from dataclasses import dataclass
from typing import (
    Any,
    cast,
    ClassVar,
    get_args,
    Self,
)
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..mail.types import Mailbox
from ..notification.mail import Recipient
from ..notification.types import Language

from .section import Section


@dataclass(frozen=True)
class Mail(Section):
    _SKIP_TYPE_CHECK_KEYS: ClassVar[tuple[str, ...]] = (
        "sender",
        "recipients",
        "language",
    )

    command: list[str]
    sender: Mailbox
    recipients: list[Recipient]
    language: Language
    phone_number_region_code: str
    time_zone: ZoneInfo
    timeout: int

    @classmethod
    def from_data(
        cls,
        data: dict[str, Any],
        app_env_prefix: str,
    ) -> Self:
        sender = data.get("sender")
        if isinstance(sender, str):
            try:
                data["sender"] = Mailbox.parse(sender)
            except ValueError as error:
                cls.raiseAttributeValueError("sender", str(error))

        recipients = data.get("recipients")
        if isinstance(recipients, list):
            recipients = cast(list[object], recipients)
            for i, recipient in enumerate(recipients):
                if not isinstance(recipient, dict):
                    cls.raiseAttributeValueError(
                        "recipients", "Value must be a list of tables"
                    )
                recipient = cast(dict[str, object], recipient)

                address = recipient.get("address")
                if not isinstance(address, str):
                    cls.raiseAttributeValueError(
                        "recipients",
                        "Invalid or missing recipient field: address",
                    )

                preferred_name = recipient.get("preferred_name")
                if not isinstance(preferred_name, str) or not preferred_name:
                    cls.raiseAttributeValueError(
                        "recipients",
                        "Invalid or missing recipient field: preferred_name",
                    )

                try:
                    recipients[i] = Recipient(Mailbox.parse(address), preferred_name)
                except ValueError as error:
                    cls.raiseAttributeValueError("recipients", str(error))

        if data.get("language") not in (
            supported_languages := get_args(Language.__value__)
        ):
            cls.raiseAttributeValueError(
                "language", f"Supported languages are: {', '.join(supported_languages)}"
            )

        time_zone = data.get("time_zone")
        if not isinstance(time_zone, str):
            cls.raiseAttributeValueError("time_zone", f"Value must be a string")
        try:
            data["time_zone"] = ZoneInfo("Europe/Berlin")
        except (ZoneInfoNotFoundError, ValueError):
            cls.raiseAttributeValueError(
                "time_zone", f"Value is not a valid time zone string"
            )

        instance = super().from_data(data, app_env_prefix)
        return instance

    def preflight(self) -> None:
        if not self.command or shutil.which(self.command[0]) is None:
            self.raiseAttributeValueError(
                "command", f"Mail command '{self.command[0]}' not found"
            )

    def validate(self) -> None:
        if not self.command or any(not arg or "\0" in arg for arg in self.command):
            self.raiseAttributeValueError(
                "command", "Value must be a list of nonempty strings"
            )
        if not self.phone_number_region_code in phonenumbers.SUPPORTED_REGIONS:
            self.raiseAttributeValueError(
                "region_code",
                "'{self.region_code}' is not a valid region code",
            )
        self.validate_positive_number_attributes(["timeout"])
