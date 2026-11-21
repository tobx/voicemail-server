import phonenumbers
import wave

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from .section import Section


@dataclass
class Call(Section):
    data_directory: str
    data_retention_duration: int
    greeting_tone_gap: float
    media_timeout: int
    region_code: str
    voicemail_duration_max: int
    voicemail_duration_min: float
    voicemail_silence_threshold: float

    @classmethod
    def from_data(
        cls,
        data: dict[str, Any],
        app_env_prefix: str,
        *,
        default_data_directory: str = "",
    ) -> Self:
        if data.get("data_directory") == "" and default_data_directory:
            data["data_directory"] = default_data_directory
        instance = super().from_data(data, app_env_prefix)
        return instance

    @property
    def greeting_file(self) -> Path:
        return Path(self.data_directory) / "greeting.wav"

    def preflight(self) -> float:
        with wave.open(str(self.greeting_file), "rb") as audio:
            if (
                audio.getframerate() != 16_000
                or audio.getsampwidth() != 2
                or audio.getnchannels() != 1
                or audio.getcomptype() != "NONE"
            ):
                self.raiseAttributeValueError(
                    "greeting_file",
                    "The audio file must be an uncompressed, 16 kHz, 16-bit, mono PCM WAV file",
                )
            duration = audio.getnframes() / audio.getframerate()
            if duration <= 0:
                self.raiseAttributeValueError(
                    "greeting_file", "The audio file must not be empty"
                )
            return duration

    def validate(self) -> None:
        self.validate_string_attributes(["data_directory"], ["nonempty", "single-line"])
        self.validate_positive_number_attributes(
            ["data_retention_duration", "media_timeout", "voicemail_duration_max"]
        )
        if not self.region_code in phonenumbers.SUPPORTED_REGIONS:
            self.raiseAttributeValueError(
                "region_code",
                "'{self.region_code}' is not a valid region code",
            )
        if (
            self.voicemail_duration_min < 0
            or self.voicemail_duration_min >= self.voicemail_duration_max
        ):
            self.raiseAttributeValueError(
                "voicemail_duration_min",
                "Value must be >= 0 and < 'voicemail_duration_max'",
            )
