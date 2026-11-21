from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

from ..call import storage
from ..mail.types import Mailbox, Mailer
from ..utility.string import sanitize_single_line
from ..utility import phonenumber

from .types import Language
from .mail_localizations import TEMPLATES


class Recipient(NamedTuple):
    mailbox: Mailbox
    preferred_name: str


class MailNotifier:
    def __init__(
        self,
        mailer: Mailer,
        sender: Mailbox,
        recipients: Sequence[Recipient],
        phone_number_region_code: str,
        language: Language = "english",
        time_zone: ZoneInfo = ZoneInfo("UTC"),
    ) -> None:
        self.mailer = mailer
        self.sender = sender
        self.recipients = recipients
        self.phone_number_region_code = phone_number_region_code
        self.template = TEMPLATES[language]
        self.time_zone = time_zone

    def notify(
        self,
        entry: storage.Entry,
        voicemail_path: Path | None,
        note: str = "",
    ) -> None:
        caller = entry.caller
        if (
            number := phonenumber.format(caller, self.phone_number_region_code)
        ) is not None:
            caller = number
        subject = self.template["subject"].format(caller=caller)
        start_time = entry.start_time.astimezone(self.time_zone)
        for recipient in self.recipients:
            body = [
                self.template["greeting"].format(recipient=recipient.preferred_name),
                "",
                self.template["info"].format(
                    caller=caller,
                    day=start_time.day,
                    month=self.template["months"][start_time.month - 1],
                    time=start_time.time().isoformat("minutes"),
                ),
                "",
            ]
            if voicemail_path is not None:
                body.extend([self.template["message"], ""])
            if note:
                safe_note = sanitize_single_line(note) or "unknown"
                body.extend([self.template["details"].format(note=safe_note), ""])
            body.extend([self.template["signature"], ""])
            attachments = [voicemail_path] if voicemail_path is not None else []
            self.mailer.send(
                self.sender,
                [recipient.mailbox],
                subject,
                "\n".join(body) + "\n",
                attachments,
            )
