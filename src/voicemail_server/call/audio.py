from __future__ import annotations

import pjsua2 as pj
import sys
import threading
import wave

from array import array
from concurrent.futures import Future
from pathlib import Path
from queue import Empty, Queue
from threading import Thread


class MediaPlayer(pj.AudioMediaPlayer):
    def __init__(self, playback_finished_event: threading.Event):
        super().__init__()
        self.playback_finished_event = playback_finished_event

    def onEof2(self):
        self.playback_finished_event.set()


class VoicemailRecorder(pj.AudioMediaPort):
    def __init__(self, writer: WavWriter):
        super().__init__()
        self.writer = writer
        format = pj.MediaFormatAudio()
        format.init(
            pj.PJMEDIA_FORMAT_PCM,
            writer.frame_rate,
            writer.channel_count,
            writer.frame_duration,
            writer.sample_width * 8,
        )
        self.createPort("voicemail", format)

    def onFrameReceived(self, frame: pj.MediaFrame) -> None:
        if frame.type != pj.PJMEDIA_FRAME_TYPE_AUDIO or frame.size == 0:
            return
        try:
            pcm = bytes(frame.buf)
            if len(pcm) != frame.size:
                raise ValueError("PCM buffer size does not match the audio frame size")
            self.writer.submit(pcm)
        except Exception as error:
            self.writer.finish(RuntimeError(f"Could not capture audio: {error}"))


class WavWriter:
    def __init__(
        self,
        path: Path,
        *,
        channel_count: int = 1,
        frame_rate: int = 16_000,  # frames per second
        sample_width: int = 2,  # bytes
        frame_duration: int = 20_000,  # microseconds
        queue_duration: float = 5.0,  # seconds
    ):
        self._queue_frames = int(queue_duration * 1_000_000 / frame_duration)
        if self._queue_frames < 1:
            raise ValueError("The recording queue must hold at least one frame")
        self.completed: Future[None] = Future()
        self.completed.set_running_or_notify_cancel()
        self._path = path
        self._channel_count = channel_count
        self._frame_rate = frame_rate
        self._sample_width = sample_width
        self._frame_duration = frame_duration
        # Reserve one extra slot for the end marker, even when audio fills the queue.
        self._queue: Queue[bytes | None] = Queue(maxsize=self._queue_frames + 1)
        self._lock = threading.Lock()
        self._accepting = True
        self._error: Exception | None = None
        Thread(target=self._run, name=f"wav-{path.stem}", daemon=False).start()

    @property
    def channel_count(self):
        return self._channel_count

    @property
    def failed(self) -> bool:
        with self._lock:
            return self._error is not None

    @property
    def frame_byte_count(self):
        return (
            self._frame_rate
            * self._channel_count
            * self._sample_width
            * self._frame_duration
            // 1_000_000
        )

    @property
    def frame_duration(self):
        return self._frame_duration

    @property
    def frame_rate(self):
        return self._frame_rate

    @property
    def sample_width(self):
        return self._sample_width

    def submit(self, pcm: bytes) -> None:
        with self._lock:
            if not self._accepting:
                return
            if len(pcm) > self.frame_byte_count or len(pcm) % self._sample_width != 0:
                self._finish_locked(ValueError("Invalid PCM frame size"))
            elif self._queue.qsize() >= self._queue_frames:
                self._finish_locked(
                    BufferError("Recording queue filled; wav writer could not keep up")
                )
            elif pcm:
                self._queue.put_nowait(pcm)

    def finish(self, error: Exception | None = None) -> None:
        with self._lock:
            self._finish_locked(error)

    def _finish_locked(self, error: Exception | None = None) -> None:
        if not self._accepting:
            return
        self._error = error
        self._accepting = False
        self._queue.put_nowait(None)

    def _run(self) -> None:
        error: Exception | None = None
        try:
            with self._path.open("xb") as stream, wave.open(stream, "wb") as reader:
                reader.setnchannels(self._channel_count)
                reader.setsampwidth(self._sample_width)
                reader.setframerate(self._frame_rate)
                while (pcm := self._queue.get()) is not None:
                    if sys.byteorder != "little":
                        samples = array("h", pcm)
                        samples.byteswap()
                        pcm = samples.tobytes()
                    reader.writeframesraw(pcm)
        except Exception as caught:
            error = caught
        with self._lock:
            self._accepting = False
            self._error = error or self._error
            error = self._error
            while True:
                try:
                    self._queue.get_nowait()
                except Empty:
                    break
        if error is None:
            self.completed.set_result(None)
        else:
            self.completed.set_exception(error)
