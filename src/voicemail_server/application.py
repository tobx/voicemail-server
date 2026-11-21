import fcntl
import logging
import pjsua2 as pj
import subprocess
import threading
import time
import wave

from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta
from importlib.resources import as_file, files
from pathlib import Path
from wave import Wave_read

from . import call
from .call import storage
from .configuration import Configuration
from .mail import gnu
from .notification.types import Notifier
from .notification.mail import MailNotifier
from .utility.audio import concatenate_wav_audio

logger = logging.getLogger(__name__)


class Application:
    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, config: Configuration, stop_event: threading.Event) -> None:
        if not config.call.greeting_file.exists():
            self.set_greeting(config)
        greeting_duration = config.preflight()
        data_dir = Path(config.call.data_directory)
        with lock_data_dir(data_dir):
            call_storage_service = storage.Service(
                data_dir,
                timedelta(days=config.call.data_retention),
                config.call.voicemail_duration_min,
                config.call.voicemail_silence_threshold,
            )
            mailer = gnu.Mailer(config.mail.command, config.mail.timeout)
            notifier = MailNotifier(
                mailer,
                config.mail.sender,
                config.mail.recipients,
                config.mail.phone_number_region_code,
                config.mail.language,
                config.mail.time_zone,
            )
            with ThreadPoolExecutor(
                max_workers=2, thread_name_prefix=self.name
            ) as workers:

                def deliver(
                    entry: storage.Entry,
                    note: str,
                    recording_completed: Future[None] | None,
                ):
                    workers.submit(
                        notify_call,
                        call_storage_service,
                        notifier,
                        entry,
                        note,
                        recording_completed,
                    )

                endpoint = pj.Endpoint()
                account = None
                endpoint.libCreate()
                try:
                    endpoint_config = pj.EpConfig()
                    endpoint_config.uaConfig.threadCnt = 0
                    endpoint_config.uaConfig.mainThreadOnly = True
                    endpoint_config.logConfig.level = config.sip.log_level
                    endpoint_config.logConfig.consoleLevel = (
                        config.sip.console_log_level
                    )
                    endpoint_config.logConfig.msgLogging = (
                        config.sip.include_sip_log_messages
                    )
                    # A headless server needs the null device to keep driving the conference bridge between calls.
                    endpoint_config.medConfig.sndAutoCloseTime = -1
                    endpoint.libInit(endpoint_config)

                    transport_cfg = pj.TransportConfig()
                    transport_cfg.port = config.sip.port
                    endpoint.transportCreate(pj.PJSIP_TRANSPORT_UDP, transport_cfg)
                    endpoint.libStart()
                    endpoint.audDevManager().setNullDev()

                    account_cfg = pj.AccountConfig()
                    account_cfg.idUri = f"sip:{config.sip.account}@{config.sip.domain}"
                    account_cfg.regConfig.registrarUri = f"sip:{config.sip.domain}"
                    if config.sip.proxy:
                        account_cfg.sipConfig.proxies.append(config.sip.proxy)
                    account_cfg.sipConfig.authCreds.append(
                        pj.AuthCredInfo(
                            "digest", "*", config.sip.account, 0, config.sip.password
                        )
                    )
                    account_cfg.natConfig.sdpNatRewriteUse = 1
                    account = call.Account(
                        call_storage_service,
                        call.Options(
                            media_timeout=config.call.media_timeout,
                            voicemail_duration_max=config.call.voicemail_duration_max,
                            greeting_file=config.call.greeting_file,
                            greeting_duration=greeting_duration,
                        ),
                    )
                    account.create(account_cfg)
                    logger.info(
                        "Voicemail server started; call log: %s",
                        call_storage_service.log_path,
                    )

                    while not stop_event.is_set():
                        endpoint.libHandleEvents(config.sip.event_timeout)
                        now = time.monotonic()
                        account.process(now, deliver)
                finally:
                    try:
                        if account is not None:
                            account.stopping = True
                            try:
                                endpoint.hangupAllCalls()
                                # Allow normal disconnect callbacks before releasing native objects.
                                shutdown_deadline = time.monotonic() + 3
                                while (
                                    account.calls
                                    and time.monotonic() < shutdown_deadline
                                ):
                                    endpoint.libHandleEvents(config.sip.event_timeout)
                                    account.process(time.monotonic(), deliver)
                            except pj.Error:
                                logger.exception(
                                    "Error while hanging up calls during shutdown"
                                )
                            finally:
                                account.finish_all(deliver)
                                try:
                                    account.shutdown()
                                finally:
                                    account = None
                    finally:
                        endpoint.libDestroy()

    def set_greeting(self, config: Configuration, path: Path | None = None) -> None:
        tone_gap = config.call.greeting_tone_gap
        output_path = config.call.greeting_file
        if path is None:
            with as_file(files(__package__).joinpath("assets/greeting.wav")) as path:
                with wave.open(str(path), "rb") as audio:
                    self.process_greeting(audio, output_path, tone_gap)
        else:
            with wave.open(str(path), "rb") as audio:
                if (
                    audio.getframerate() != 16_000
                    or audio.getsampwidth() != 2
                    or audio.getnchannels() != 1
                    or audio.getcomptype() != "NONE"
                ):
                    raise ValueError(
                        f"The greeting audio file must be an uncompressed, 16 kHz, 16-bit, mono PCM WAV file"
                    )
                duration = audio.getnframes() / audio.getframerate()
                if duration <= 0:
                    raise ValueError(f"The audio file must not be empty")
                self.process_greeting(audio, output_path, tone_gap)

    def process_greeting(
        self, greeting_audio: Wave_read, output_path: Path, tone_gap: float
    ) -> None:
        with as_file(files(__package__).joinpath("assets/tone.wav")) as path:
            with wave.open(str(path), "rb") as tone_audio:
                concatenate_wav_audio(
                    greeting_audio,
                    tone_audio,
                    output_path=output_path,
                    gap=tone_gap,
                )


def notify_call(
    call_storage_service: storage.Service,
    notifier: Notifier,
    entry: storage.Entry,
    note: str,
    recording_completed: Future[None] | None,
):
    voicemail_path = None
    try:
        try:
            if recording_completed is not None:
                recording_completed.result()
            voicemail_path = call_storage_service.log_finished_call(entry)
        except Exception:
            logger.exception("Could not prepare voicemail for call %s", entry.id)
            note = f"{note} The recording could not be completed or read; check the local call log/audio folder.".strip()
        try:
            notifier.notify(entry, voicemail_path, note)
            logger.info("Notification submitted to mail for call %s", entry.id)
        except subprocess.CalledProcessError as error:
            logger.error(
                "mail failed for call %s (exit %s): %s",
                entry.id,
                error.returncode,
                error.stderr,
            )
        except Exception:
            logger.exception(
                "Could not send notification for call %s; any voicemail remains at %s",
                entry.id,
                entry.voicemail_path,
            )
    finally:
        call_storage_service.discard_protection(entry)
        try:
            call_storage_service.cleanup()
        except Exception:
            logger.exception("Retention cleanup failed")


@contextmanager
def lock_data_dir(data_dir: Path):
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (data_dir / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(
                f"Another process has locked the data directory '{data_dir}'"
            ) from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
