import sys
import wave

from array import array
from pathlib import Path
from wave import Wave_read


def concatenate_wav_audio(
    *readers: Wave_read, output_path: str | Path, gap: float = 0.0
) -> None:
    params = readers[0].getparams()

    if gap > 0.0:
        silence_frame_count = int(params.framerate * gap)
        silence = b"\x00" * params.nchannels * params.sampwidth * silence_frame_count
    else:
        silence = None

    with wave.open(str(output_path), "wb") as out:
        out.setparams(params)
        for i, audio in enumerate(readers):
            current = audio.getparams()
            assert (
                current.nchannels == params.nchannels
                and current.sampwidth == params.sampwidth
                and current.framerate == params.framerate
                and current.comptype == params.comptype
            )
            out.writeframes(audio.readframes(audio.getnframes()))
            if silence is not None and i < len(readers) - 1:
                out.writeframes(silence)


def decode(samples: bytes, sample_width: int) -> list[int] | array[int]:
    match sample_width:
        case 1:
            return [sample - 128 for sample in samples]
        case 2:
            decoded = array("h", samples)
            if sys.byteorder != "little":
                decoded.byteswap()
            return decoded
        case 3:
            return [
                int.from_bytes(samples[i : i + 3], "little", signed=True)
                for i in range(0, len(samples), 3)
            ]
        case _:
            decoded = array("i", samples)
            if sys.byteorder != "little":
                decoded.byteswap()
            return decoded


def is_audible(
    reader: wave.Wave_read,
    silence_threshold: float,  # dBFS (0 or greater disables the threshold)
    min_duration: float = 0,
) -> bool:
    if reader.getcomptype() != "NONE":
        raise ValueError(f"Unsupported WAV compression type: {reader.getcomptype()}")

    supported_sample_widths = (1, 2, 3, 4)
    sample_width = reader.getsampwidth()
    if sample_width not in supported_sample_widths:
        raise ValueError(f"Unsupported WAV sample width: '{sample_width}'")

    start_frame = reader.tell()
    channel_count = reader.getnchannels()
    frame_rate = reader.getframerate()
    frames_per_block = max(1, frame_rate // 50)
    frame_size = channel_count * sample_width
    max_amplitude = (1 << (sample_width * 8 - 1)) - 1
    audible = silence_threshold >= 0
    rms_threshold_squared = 10 ** (silence_threshold / 10)

    while frames := reader.readframes(frames_per_block):
        if len(frames) % frame_size != 0:
            raise ValueError("Truncated PCM frame found")
        if not audible:
            samples = decode(frames, sample_width)
            audible = sum(
                (sample / max_amplitude) ** 2 for sample in samples
            ) > rms_threshold_squared * len(samples)
        if audible and (reader.tell() - start_frame) / frame_rate >= min_duration:
            return True

    return False
