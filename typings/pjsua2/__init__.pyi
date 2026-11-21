from typing import Any
from collections.abc import Sequence

PJSIP_INV_STATE_NULL: int
PJSIP_INV_STATE_CALLING: int
PJSIP_INV_STATE_INCOMING: int
PJSIP_INV_STATE_EARLY: int
PJSIP_INV_STATE_CONNECTING: int
PJSIP_INV_STATE_CONFIRMED: int
PJSIP_INV_STATE_DISCONNECTED: int

PJMEDIA_TYPE_AUDIO: int
PJMEDIA_TYPE_VIDEO: int
PJMEDIA_TYPE_APPLICATION: int
PJSUA_CALL_MEDIA_ACTIVE: int
PJSUA_CALL_MEDIA_LOCAL_HOLD: int
PJSUA_CALL_MEDIA_REMOTE_HOLD: int
PJSUA_CALL_MEDIA_ERROR: int
PJMEDIA_FILE_NO_LOOP: int
PJMEDIA_FORMAT_PCM: int
PJMEDIA_FRAME_TYPE_AUDIO: int

PJSIP_TRANSPORT_UDP: int
PJSIP_TRANSPORT_TCP: int
PJSIP_TRANSPORT_TLS: int

class Error(Exception):
    def info(self) -> str: ...

class UaConfig:
    threadCnt: int
    mainThreadOnly: bool

class LogConfig:
    level: int
    consoleLevel: int
    msgLogging: bool

class MediaConfig:
    sndAutoCloseTime: int

class EpConfig:
    uaConfig: UaConfig
    logConfig: LogConfig
    medConfig: MediaConfig

class TransportConfig:
    port: int

class AuthCredInfo:
    def __init__(
        self,
        scheme: str,
        realm: str,
        username: str,
        data_type: int,
        data: str,
    ) -> None: ...

class RegConfig:
    registrarUri: str

class SipConfig:
    proxies: Any
    authCreds: Any

class NatConfig:
    sdpNatRewriteUse: int

class AccountConfig:
    idUri: str
    regConfig: RegConfig
    sipConfig: SipConfig
    natConfig: NatConfig

class CallSetting:
    audioCount: int
    videoCount: int

class CallOpParam:
    statusCode: int
    opt: CallSetting

    def __init__(self, useDefault: bool = ...) -> None: ...

class CallInfo:
    remoteUri: str
    state: int
    stateText: str
    media: list[CallMediaInfo]

class CallMediaInfo:
    type: int
    status: int
    index: int

class CallMedia:
    pass

class AudioMedia:
    def startTransmit(self, sink: AudioMedia) -> None: ...
    def stopTransmit(self, sink: AudioMedia) -> None: ...

class AudioMediaPlayer(AudioMedia):
    def __init__(self) -> None: ...
    def createPlayer(self, fileName: str, options: int = ...) -> None: ...
    def startTransmit(self, sink: AudioMedia) -> None: ...
    def stopTransmit(self, sink: AudioMedia) -> None: ...
    def onEof2(self) -> None: ...

class MediaFormatAudio:
    def init(
        self,
        formatId: int,
        clockRate: int,
        channelCount: int,
        frameTimeUsec: int,
        bitsPerSample: int,
        avgBps: int = ...,
        maxBps: int = ...,
    ) -> None: ...

class MediaFrame:
    type: int
    buf: Sequence[int]
    size: int

class AudioMediaPort(AudioMedia):
    def __init__(self) -> None: ...
    def createPort(self, name: str, fmt: MediaFormatAudio) -> None: ...
    def onFrameReceived(self, frame: MediaFrame) -> None: ...

class AudioMediaRecorder(AudioMedia):
    def __init__(self) -> None: ...
    def createRecorder(
        self,
        fileName: str,
        encType: int = ...,
        maxSize: int = ...,
        options: int = ...,
    ) -> None: ...

class Call:
    def __init__(self, account: Account, call_id: int = ...) -> None: ...
    def getInfo(self) -> CallInfo: ...
    def getAudioMedia(self, med_idx: int) -> AudioMedia: ...
    def answer(self, prm: CallOpParam) -> None: ...
    def hangup(self, prm: CallOpParam) -> None: ...
    def onCallState(self, prm: Any) -> None: ...
    def onCallMediaState(self, prm: Any) -> None: ...

class AccountInfo:
    regStatus: int
    regStatusText: str
    regIsActive: bool

class OnIncomingCallParam:
    callId: int

class RegStateParam:
    pass

class Account:
    def __init__(self) -> None: ...
    def create(self, cfg: AccountConfig) -> None: ...
    def shutdown(self) -> None: ...
    def getInfo(self) -> AccountInfo: ...
    def onRegState(self, prm: Any) -> None: ...
    def onIncomingCall(self, prm: OnIncomingCallParam) -> None: ...

class AudioDeviceManager:
    def setNullDev(self) -> None: ...

class Endpoint:
    def __init__(self) -> None: ...
    def libCreate(self) -> None: ...
    def libInit(self, prm: EpConfig) -> None: ...
    def libStart(self) -> None: ...
    def libDestroy(self) -> None: ...
    def transportCreate(self, transportType: int, cfg: TransportConfig) -> int: ...
    def audDevManager(self) -> AudioDeviceManager: ...
    def libHandleEvents(self, msecTimeout: int = ...) -> int: ...
    def hangupAllCalls(self) -> None: ...
