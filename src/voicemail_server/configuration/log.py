from dataclasses import dataclass
from typing import Any, ClassVar, Literal, Self, get_args

from .section import Section

Level = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass(frozen=True)
class Log(Section):
    _SKIP_TYPE_CHECK_KEYS: ClassVar[tuple[str, ...]] = ("level",)

    level: Level

    @classmethod
    def from_data(
        cls,
        data: dict[str, Any],
        app_env_prefix: str,
    ) -> Self:
        if not data.get("level") in get_args(Level):
            cls.raiseAttributeValueError("level", f"Value is not a valid log level")
        instance = super().from_data(data, app_env_prefix)
        return instance
