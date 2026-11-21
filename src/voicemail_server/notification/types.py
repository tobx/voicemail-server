from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from ..call import storage

type Language = Literal["english", "german"]


@dataclass
class CallReceived:
    entry: storage.Entry
    voicemail_path: Path


class Notifier(Protocol):
    def notify(
        self,
        entry: storage.Entry,
        voicemail_path: Path | None,
        note: str = "",
    ) -> None: ...
