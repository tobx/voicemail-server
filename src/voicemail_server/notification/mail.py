import phonenumbers as pn

from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

from .. import contacts
from ..call import storage
from ..mail.types import Mailbox, Mailer
from ..utility.string import sanitize_single_line

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
        language: Language = "english",
        time_zone: ZoneInfo = ZoneInfo("UTC"),
        contacts: contacts.Service | None = None,
    ) -> None:
        self.mailer = mailer
        self.sender = sender
        self.recipients = recipients
        self.template = TEMPLATES[language]
        self.time_zone = time_zone
        self.contacts = contacts

    def notify(
        self,
        entry: storage.Entry,
        voicemail_path: Path | None,
        note: str = "",
    ) -> None:
        caller = entry.caller
        name = ""
        if isinstance(caller, pn.PhoneNumber):
            if self.contacts is not None:
                name = self.contacts.find_contact_name(caller)
            caller = pn.format_number(caller, pn.PhoneNumberFormat.INTERNATIONAL)
        subject = self.template["subject"].format(caller=name if name else caller)
        start_time = entry.start_time.astimezone(self.time_zone)
        for recipient in self.recipients:
            body = [
                self.template["greeting"].format(recipient=recipient.preferred_name),
                "",
                self.template["info"].format(
                    caller=f"{name} ({caller})" if name else caller,
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
