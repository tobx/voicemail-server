from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .account import Account

import logging
import pjsua2 as pj
import threading
import time

from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path

from ..utility import sip

from .audio import MediaPlayer, VoicemailRecorder, WavWriter

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class Options:
    media_timeout: int
    voicemail_duration_max: int
    greeting_file: Path
    greeting_duration: float


class Call(pj.Call):
    def __init__(
        self,
        account: Account,
        call_id: int,
    ):
        super().__init__(account, call_id)
        try:
            caller = sip.extract_user_from_name_addr(self.getInfo().remoteUri)
        except pj.Error:
            logger.exception("Could not parse incoming caller number")
            caller = ""
        self.entry = account.call_storage_service.log_call_start(caller)
        self.options = account.call_options
        self.player = None
        self.voicemail_recorder = None
        self.voicemail_writer: WavWriter | None = None
        self.audio_media = None
        self.playback_finished_event = threading.Event()
        self.media_changed = True
        self.confirmed = False
        self.disconnected = False
        self.hangup_sent = False
        self.state = "waiting"
        self.note = ""
        self.voicemail_deadline = None
        self.finish_deadline = None
        self.call_deadline = time.monotonic() + (
            self.options.media_timeout
            + self.options.greeting_duration
            + self.options.voicemail_duration_max
        )
        self.media_deadline = time.monotonic() + self.options.media_timeout

    @property
    def recording_completed(self) -> Future[None] | None:
        return self.voicemail_writer.completed if self.voicemail_writer else None

    def advance(self, now: float):
        if self.disconnected:
            return
        if self.state == "finishing":
            if self.finish_deadline is not None and now >= self.finish_deadline:
                self.note = f"{self.note} SIP disconnect was not confirmed before local cleanup.".strip()
                self.disconnected = True
            return
        if now >= self.call_deadline or (
            self.state == "waiting" and now >= self.media_deadline
        ):
            self.finish("Timed out waiting for call audio or call completion.")
            return
        try:
            if self.voicemail_writer is not None and self.voicemail_writer.failed:
                self.finish(
                    "Audio recording failed; check the local call log/audio folder."
                )
                return
            if self.confirmed and self.media_changed:
                self._refresh_media()
            if (
                self.confirmed
                and self.state == "waiting"
                and self.audio_media is not None
            ):
                self._start_playback()
            if self.state == "greeting" and self.playback_finished_event.is_set():
                self._start_recording(now)
            if (
                self.state == "recording"
                and self.voicemail_deadline is not None
                and now >= self.voicemail_deadline
            ):
                self.finish("The maximum message length was reached.")
        except (pj.Error, OSError, RuntimeError) as error:
            detail = error.info() if isinstance(error, pj.Error) else str(error)
            logger.exception("Audio failed for call %s", self.entry.id)
            self.finish(f"Audio error: {detail}")

    def close_media(self):
        """Stop capture; the delivery worker waits for WAV finalization."""
        self._stop_playback()
        self._stop_recording()
        self.audio_media = None

    def finish(self, note: str = ""):
        if note:
            self.note = note
        self.close_media()
        self.state = "finishing"
        if self.finish_deadline is None:
            self.finish_deadline = time.monotonic() + 3
        if self.disconnected or self.hangup_sent:
            return
        try:
            self.hangup(pj.CallOpParam())
            self.hangup_sent = True
        except pj.Error:
            logger.exception("Hangup failed for call %s", self.entry.id)

    def onCallMediaState(self, prm: object):
        self.media_changed = True

    def onCallState(self, prm: object):
        try:
            info = self.getInfo()
            logger.info(
                "Call %s (%s): %s", self.entry.id, self.entry.caller, info.stateText
            )
            if info.state == pj.PJSIP_INV_STATE_DISCONNECTED:
                self.disconnected = True
            elif info.state == pj.PJSIP_INV_STATE_CONFIRMED:
                self.confirmed = True
                self.media_changed = True
        except pj.Error:
            logger.exception("Could not read state for call %s", self.entry.id)

    def _detach_routes(self):
        if self.audio_media is None:
            return
        if self.player is not None:
            try:
                self.player.stopTransmit(self.audio_media)
            except pj.Error:
                # a disconnected or replaced conference port is already gone
                pass
        if self.voicemail_recorder is not None:
            try:
                self.audio_media.stopTransmit(self.voicemail_recorder)
            except pj.Error:
                pass

    def _refresh_media(self):
        self.media_changed = False
        new_audio_media = None
        info = self.getInfo()
        for media in info.media:
            if (
                media.type == pj.PJMEDIA_TYPE_AUDIO
                and media.status == pj.PJSUA_CALL_MEDIA_ACTIVE
            ):
                new_audio_media = self.getAudioMedia(media.index)
                break
        # Reconnect existing objects even if a replacement stream reuses a port ID.
        self._detach_routes()
        self.audio_media = new_audio_media
        if new_audio_media is not None:
            if self.player is not None:
                self.player.startTransmit(new_audio_media)
            if self.voicemail_recorder is not None:
                new_audio_media.startTransmit(self.voicemail_recorder)

    def _start_playback(self):
        if self.audio_media is None:
            return
        self.player = MediaPlayer(self.playback_finished_event)
        self.player.createPlayer(
            str(self.options.greeting_file), pj.PJMEDIA_FILE_NO_LOOP
        )
        self.player.startTransmit(self.audio_media)
        self.state = "greeting"
        logger.info("Playing greeting to %s", self.entry.caller)

    def _start_recording(self, now: float):
        self._stop_playback()
        self.voicemail_writer = WavWriter(self.entry.voicemail_path)
        self.voicemail_recorder = VoicemailRecorder(self.voicemail_writer)
        if self.audio_media is not None:
            self.audio_media.startTransmit(self.voicemail_recorder)
        self.state = "recording"
        self.voicemail_deadline = now + self.options.voicemail_duration_max
        logger.info("Recording message from %s", self.entry.caller)

    def _stop_playback(self):
        if self.player is not None:
            if self.audio_media is not None:
                try:
                    self.player.stopTransmit(self.audio_media)
                except pj.Error:
                    pass
            self.player = None

    def _stop_recording(self):
        # Seal before disconnecting: native route removal is asynchronous, so
        # callbacks arriving during cleanup must not append after the end marker.
        if self.voicemail_writer is not None:
            self.voicemail_writer.finish()
        if self.voicemail_recorder is not None:
            if self.audio_media is not None:
                try:
                    self.audio_media.stopTransmit(self.voicemail_recorder)
                except pj.Error:
                    pass
            self.voicemail_recorder = None
