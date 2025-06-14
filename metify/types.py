"""Core type definitions for the high-performance modeling library."""

from __future__ import annotations

from typing import Any, TypeAlias, TypeVar, TypedDict
from collections.abc import Callable

T = TypeAlias = TypeVar('T')

JSONScalars = (
    str | int | float | bool | None
)
JSONEncodable = (
    JSONScalars | list[Any] | dict[str, Any] | tuple[Any, ...]
)


FactoryFn= Callable[[T], T]
ValidatorFn = Callable[[Any], Any]
SerializerFn = Callable[[T], Any]
AliasGenerator = Callable[[str], str]

JSONEncoderMapping = dict[type[T], Callable[[T], JSONEncodable]]

class ModelConfig(TypedDict, total=False):
    """Complete configuration dictionary for ModelBase classes."""
    serialize_by_alias: bool
    alias_generator: AliasGenerator
    json_encoding_handler: JSONEncoderMapping
    repr: bool
    init: bool
    slots: bool
    frozen: bool

