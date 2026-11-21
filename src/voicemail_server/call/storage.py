import logging
import os
import phonenumbers as pn
import re
import tempfile
import threading
import wave

from dataclasses import dataclass
from datetime import datetime
from datetime import datetime, timedelta
from pathlib import Path
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
from uuid import uuid4

from ..utility import audio
from ..utility.string import sanitize_single_line
from ..utility.time import utc

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Entry:
    id: str
    start_time: datetime
    caller: pn.PhoneNumber | str
    voicemail_path: Path

    def format_caller(self) -> str:
        if isinstance(self.caller, pn.PhoneNumber):
            return pn.format_number(self.caller, pn.PhoneNumberFormat.E164)
        else:
            return self.caller


class Service:
    _RE: ClassVar[SimpleNamespace] = SimpleNamespace(
        message_id=re.compile(r"[0-9a-f]{32}"),
        voicemail_filename=re.compile(
            r"^(?P<stamp>\d{8}T\d{6}\.\d{6}Z)_.+_(?P<id>[0-9a-f]{32})\.wav$"
        ),
    )

    def __init__(
        self,
        data_dir: Path,
        retention_duration: timedelta,
        region_code: str,
        min_voicemail_duration: float,
        voicemail_silence_threshold: float,
    ) -> None:
        self._data_dir = data_dir
        self._voicemail_dir = data_dir / "voicemails"
        self._log_path = data_dir / "calls.log"
        self._retention_duration = retention_duration
        self._region_code = region_code
        self._min_voicemail_duration = min_voicemail_duration
        self._voicemail_silence_threshold = voicemail_silence_threshold
        self._lock = threading.RLock()
        self._protected: set[str] = set()
        self._voicemail_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        # Create log file and verify log file permissions
        os.close(os.open(self._log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600))

    @property
    def log_path(self) -> Path:
        return self._log_path

    def cleanup(self) -> None:
        retention_cutoff = utc() - self._retention_duration
        with self._lock:
            self._prune_call_log(retention_cutoff)
            self._prune_voicemails(retention_cutoff)

    def discard_protection(self, entry: Entry) -> None:
        with self._lock:
            self._protected.discard(entry.id)

    def log_call_start(self, raw_caller: str) -> Entry:
        start_time = utc()
        caller = sanitize_single_line(raw_caller) or "unknown"
        try:
            caller = pn.parse(caller, self._region_code)
        except pn.NumberParseException:
            pass
        if isinstance(caller, pn.PhoneNumber):
            safe_caller = pn.format_number(caller, pn.PhoneNumberFormat.E164)
        else:
            safe_caller = re.sub(r"[^A-Za-z0-9+_.-]", "_", caller)[:80]
        call_id = uuid4().hex
        timestamp = start_time.isoformat()
        voicemail_path = (
            self._voicemail_dir / f"{timestamp}_{safe_caller}_{call_id}.wav"
        )
        entry = Entry(
            id=call_id,
            start_time=start_time,
            caller=caller,
            voicemail_path=voicemail_path,
        )
        call_log_line = f"{start_time.isoformat(timespec='microseconds')}\t{entry.format_caller()}\t{call_id}\n"
        # Protect call entry from retention
        with self._lock:
            self._protected.add(call_id)
            try:
                with self._log_path.open("a", encoding="utf-8") as stream:
                    stream.write(call_log_line)
            except OSError:
                logger.exception(
                    "Could not append call %s to %s", call_id, self._log_path
                )
        return entry

    def log_finished_call(self, entry: Entry) -> Path | None:
        voicemail_path = entry.voicemail_path
        try:
            voicemail_size = voicemail_path.stat().st_size
        except FileNotFoundError:
            return None
        if voicemail_size == 0:
            voicemail_path.unlink(missing_ok=True)
            return None
        if self._voicemail_is_audible(voicemail_path):
            return voicemail_path
        voicemail_path.unlink(missing_ok=True)
        return None

    def _is_expired_log_line(self, line: str, retention_cutoff: datetime) -> bool:
        fields = line.rstrip("\n").split("\t")
        if len(fields) != 3:
            return False
        stamp, _, call_id = fields
        if self._RE.message_id.fullmatch(call_id) is None:
            return False
        try:
            timestamp = datetime.fromisoformat(stamp)
        except ValueError:
            return False
        return timestamp < retention_cutoff and call_id not in self._protected

    def _prune_call_log(self, retention_cutoff: datetime) -> None:
        temp_log_path: Path | None = None
        entries_were_removed = False
        try:
            with (
                self._log_path.open(encoding="utf-8") as original,
                tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self._data_dir,
                    prefix=".calls-",
                    suffix=".tmp",
                    delete=False,
                ) as temp_log,
            ):
                temp_log_path = Path(temp_log.name)
                for line in original:
                    if self._is_expired_log_line(line, retention_cutoff):
                        entries_were_removed = True
                        continue
                    temp_log.write(line)

                if entries_were_removed:
                    temp_log.flush()
                    os.fsync(temp_log.fileno())

            if entries_were_removed:
                os.replace(temp_log_path, self._log_path)
        finally:
            if temp_log_path is not None:
                temp_log_path.unlink(missing_ok=True)

    def _prune_voicemails(self, retention_cutoff: datetime) -> None:
        for path in self._voicemail_dir.iterdir():
            match = self._RE.voicemail_filename.fullmatch(path.name)
            if match is None or not path.is_file() or match["id"] in self._protected:
                continue
            try:
                timestamp = datetime.fromisoformat(match["stamp"])
            except ValueError:
                continue
            if timestamp >= retention_cutoff:
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not expire voicemail %s", path)

    def _voicemail_is_audible(self, path: Path) -> bool:
        try:
            with wave.open(str(path), "rb") as reader:
                return audio.is_audible(
                    reader,
                    self._voicemail_silence_threshold,
                    self._min_voicemail_duration,
                )
        except (wave.Error, EOFError, ValueError) as error:
            raise ValueError(f"Cannot read voicemail '{path.name}': {error}") from error
