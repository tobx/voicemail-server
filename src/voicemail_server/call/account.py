import logging
import pjsua2 as pj

from collections.abc import Callable
from concurrent.futures import Future

from . import call, storage
from .call import Call

logger = logging.getLogger(__name__)


class Account(pj.Account):
    def __init__(
        self, call_storage_service: storage.Service, call_options: call.Options
    ):
        super().__init__()
        self.call_storage_service = call_storage_service
        self.call_options = call_options
        self.calls: set[Call] = set()
        self.stopping = False

    def onRegState(self, prm: object):
        info = self.getInfo()
        logger.info(
            "Registration: %s %s (active=%s)",
            info.regStatus,
            info.regStatusText,
            info.regIsActive,
        )

    def onIncomingCall(self, prm: pj.OnIncomingCallParam):
        call = Call(self, prm.callId)
        self.calls.add(call)
        logger.info("Incoming call from %s", call.entry.format_caller())
        response = pj.CallOpParam(True)
        response.statusCode = 503 if self.stopping else 200
        response.opt.audioCount = 1
        response.opt.videoCount = 0
        try:
            call.answer(response)
        except pj.Error as error:
            logger.exception("Answer failed for call %s", call.entry.id)
            call.finish(f"Could not answer the call: {error.info()}")

    def process(
        self,
        now: float,
        deliver: Callable[[storage.Entry, str, Future[None] | None], None],
    ):
        for call in tuple(self.calls):
            call.advance(now)
            if call.disconnected:
                call.close_media()
                self.calls.remove(call)
                deliver(call.entry, call.note, call.recording_completed)

    def finish_all(
        self, deliver: Callable[[storage.Entry, str, Future[None] | None], None]
    ) -> None:
        for call in tuple(self.calls):
            call.finish("The voicemail server was stopped.")
            self.calls.remove(call)
            deliver(call.entry, call.note, call.recording_completed)
