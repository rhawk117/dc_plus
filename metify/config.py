from __future__ import annotations
from collections.abc import Callable

import typing

if typing.TYPE_CHECKING:
    from .core.types import JSONEncoderMapping


class ModelConfig(typing.TypedDict, total=False):
    serialize_by_alias: bool
    strict: bool

    alias_generator: Callable[[str], str]
    exclude_none_by_default: bool

    json_default_handler: Callable[[typing.Any], typing.Any]
    json_encoders: JSONEncoderMapping

    repr: bool
    init: bool

    slots: bool
    frozen: bool