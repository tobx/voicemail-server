import mimetypes
import subprocess

from collections.abc import Sequence
from email.header import Header
from pathlib import Path

from .mailbox import Mailbox


class Mailer:
    """A mailer that wraps GNU Mailutils mail."""

    def __init__(
        self,
        command: Sequence[str] = ("mail",),
        timeout: float | None = None,
    ) -> None:
        self.command = (command,) if isinstance(command, str) else command
        self.timeout = timeout

    def send(
        self,
        sender: Mailbox,
        recipients: Sequence[Mailbox],
        subject: str,
        body: str,
        attachments: Sequence[Path] = (),
        cc_recipients: Sequence[Mailbox] = (),
        bcc_recipients: Sequence[Mailbox] = (),
    ) -> None:
        argv = [
            *self.command,
            "--mime",
            f"--append=From: {sender.format()}",
            f"--subject={Header(subject, "UTF-8").encode()}",
            *[f"--cc={recipient.format()}" for recipient in cc_recipients],
            *[f"--bcc={recipient.format()}" for recipient in bcc_recipients],
        ]
        for attachment in attachments:
            mime_type, _ = mimetypes.guess_type(attachment.name)
            argv.extend(
                [
                    f"--content-type={mime_type or 'application/octet-stream'}",
                    "--encoding=base64",
                    f"--attach={attachment}",
                ]
            )
        argv.extend(
            [
                "--content-type=text/plain; charset=UTF-8",
                "--encoding=quoted-printable",
                "--",
                *(recipient.format() for recipient in recipients),
            ]
        )
        subprocess.run(
            argv,
            input=body if body.endswith("\n") else body + "\n",
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=self.timeout,
            check=True,
        )
