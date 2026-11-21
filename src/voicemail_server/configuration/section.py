import math
import os

from abc import ABC
from typing import (
    Any,
    ClassVar,
    get_origin,
    get_type_hints,
    Literal,
    Never,
    Self,
)


class Section(ABC):
    _ENV_OVERRIDABLE_KEYS: ClassVar[tuple[str, ...]] = ()

    _SKIP_TYPE_CHECK_KEYS: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def from_data(
        cls,
        data: dict[str, Any],
        app_env_prefix: str,
    ) -> Self:
        section_key = cls.get_section_key()
        env_prefix = f"{app_env_prefix}_{section_key.upper()}_"
        for key in cls._ENV_OVERRIDABLE_KEYS:
            env_var_name = f"{env_prefix}{key.upper()}"
            if (value := os.environ.get(env_var_name)) is not None:
                data[key] = value
            if key not in data:
                raise ValueError(
                    f"Either the configuration key '{key}' in section '{section_key}' or the OS environment variable '{env_var_name}' must be set"
                )
        expected_types = {
            key: expected
            for key, expected in get_type_hints(cls).items()
            if get_origin(expected) is not ClassVar
        }
        if invalid_keys := {
            key
            for key, expected in expected_types.items()
            if key not in cls._SKIP_TYPE_CHECK_KEYS
            and not isinstance(
                data.get(key),
                (int, float) if expected is float else get_origin(expected) or expected,
            )
        }:
            formated_keys = ", ".join(sorted(invalid_keys))
            raise ValueError(
                f"Invalid or missing configuration key(s) in section '{section_key}': {formated_keys}"
            )
        instance = cls(**{key: data[key] for key in expected_types})
        instance.validate()
        return instance

    @classmethod
    def get_section_key(cls) -> str:
        return cls.__name__.lower()

    @classmethod
    def raiseAttributeValueError(cls, attribute_name: str, message: str) -> Never:
        raise ValueError(
            f"Configuration section: {cls.get_section_key()}, key: {attribute_name}, error: {message}"
        )

    def validate(self) -> None:
        pass

    def validate_number_attribute_ranges(
        self, ranges: list[tuple[str, int | float, int | float]]
    ) -> None:
        for name, min, max in ranges:
            value = getattr(self, name)
            if value < min or value > max:
                self.raiseAttributeValueError(
                    name, f"Value must be in the range [{min}, {max}]"
                )

    def validate_positive_number_attributes(self, attribute_names: list[str]) -> None:
        for name in attribute_names:
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                self.raiseAttributeValueError(
                    name, "Value must be a positive finite number"
                )

    def validate_string_attributes(
        self,
        attribute_names: list[str],
        constraints: list[Literal["nonempty", "single-line"]],
    ) -> None:
        for name in attribute_names:
            value = getattr(self, name)
            if "nonempty" in constraints and not value.strip():
                self.raiseAttributeValueError(name, "Value must be a nonempty string")
            if "single-line" in constraints and any(c in value for c in "\r\n\x00"):
                self.raiseAttributeValueError(
                    name, "Value must be a single-line string"
                )
