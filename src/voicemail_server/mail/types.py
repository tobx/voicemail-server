from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from .mailbox import Mailbox


class Mailer(Protocol):
    def send(
        self,
        sender: Mailbox,
        recipients: Sequence[Mailbox],
        subject: str,
        body: str,
        attachments: Sequence[Path] = (),
        cc_recipients: Sequence[Mailbox] = (),
        bcc_recipients: Sequence[Mailbox] = (),
    ) -> None: ...
