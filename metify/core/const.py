"""
**dc_plus.common.const**

Contains commonly used constants, error messages, and string literals for the ModelBase
framework to maintain consistency and avoid magic strings throughout the codebase.

"""
from typing import Final



FIELDS_CLS_VAR = '__mtf_fields__'
ALIAS_MAP_CLS_VAR = '__mtf_alias_map__'
EXTRAS_CLS_VAR = '__mtf_extras__'
CONFIG_CLS_VAR_NAME = '__mtf_config__'

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
