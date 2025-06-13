from __future__ import annotations
from .core.field_cls import MetifyField
import typing

if typing.TYPE_CHECKING:
    from .core.types import FactoryFn, ValidatorFn, SerializerFn

def Meta(
    default: typing.Any = MetifyField.MISSING,
    *,
    default_factory: FactoryFn | typing.Any = MetifyField.MISSING,
    desc: str | None = None,
    alias: str | None = None,
    validator: ValidatorFn | None = None,
    serializer: SerializerFn | None = None,
    init: bool = True,
    repr: bool = True,
    **extra: typing.Any
) -> MetifyField:
    """Create a field for use in data classes with additional metadata."""
    return MetifyField(
        default=default,
        default_factory=default_factory,
        desc=desc,
        alias=alias,
        validator=validator,
        serializer=serializer,
        init=init,
        repr=repr,
        **extra
    )