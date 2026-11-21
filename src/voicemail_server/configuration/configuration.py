import tomllib

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Self

from ..utility import platform

from .call import Call
from .log import Log
from .mail import Mail
from .sip import Sip


@dataclass(frozen=True)
class Configuration:
    sip: Sip
    call: Call
    mail: Mail
    log: Log

    @classmethod
    def load(cls, path: str | Path, app_name: str) -> Self:
        path = Path(path)
        with path.open("rb") as f:
            data = tomllib.load(f)
        required_keys = {field.name for field in fields(cls)}
        if invalid_keys := {
            key for key in required_keys if not isinstance(data.get(key), dict)
        }:
            formated_keys = ", ".join(sorted(invalid_keys))
            raise ValueError(
                f"Invalid or missing configuration section(s): {formated_keys}"
            )
        app_env_prefix = app_name.upper().replace("-", "_")
        default_call_data_directory = (
            f"/var/local/lib/{app_name}" if platform.is_debian_like() else ""
        )
        return cls(
            sip=Sip.from_data(data["sip"], app_env_prefix),
            call=Call.from_data(
                data["call"],
                app_env_prefix,
                default_data_directory=default_call_data_directory,
            ),
            mail=Mail.from_data(data["mail"], app_env_prefix),
            log=Log.from_data(data["log"], app_env_prefix),
        )

    def preflight(self) -> float:
        self.mail.preflight()
        return self.call.preflight()
