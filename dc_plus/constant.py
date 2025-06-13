"""
**constant.py**

Contains commonly used constants, error messages, and string literals for the ModelBase
framework to maintain consistency and avoid magic strings throughout the codebase.

"""

from typing import Final


SERIALIZE_METHOD: Final[str] = "__serialize__"
DESERIALIZE_METHOD: Final[str] = "__deserialize__"

DESCRIPTION_KEY: Final[str] = "desc"
VALIDATOR_KEY: Final[str] = "validator"

OPTIONS_ATTR: Final[str] = "__options__"
CUSTOM_FLAGS_ATTR: Final[str] = "__custom_flags__"
FIELD_ALIASES_ATTR: Final[str] = "__field_aliases__"
REVERSE_ALIASES_ATTR: Final[str] = "__reverse_aliases__"

ORIGIN_ATTR: Final[str] = "__origin__"
ARGS_ATTR: Final[str] = "__args__"

INVALID_OPTIONS_TYPE: Final[str] = (
    "{class_name}.options must be a ModelOptions instance"
)

ALIAS_GENERATOR_MISSING: Final[str] = (
    "ModelBase: {flag_name} is True but no alias generator is set in options. "
    "Was this a mistake? "
    "\nFix: Set ModelOptions serialization_alias_generator or set {flag_name} to False."
)

JSON_DECODE_ERROR: Final[str] = "Invalid JSON string: {error}"
MODEL_CREATION_ERROR: Final[str] = "Failed to create {class_name}: {error}"

DATACLASS_KWARGS: Final[set[str]] = {
    "init",
    "repr",
    "eq",
    "order",
    "unsafe_hash",
    "frozen",
    "slots",
    "weakref_slot",
    "match_args",
    "kw_only"
}

DEFAULT_ENCODING: Final[str] = "utf-8"
