from __future__ import annotations

import dataclasses
import typing

if typing.TYPE_CHECKING:
    from .types import FactoryFn, ValidatorFn, SerializerFn

REQUIRED = ...
_MISSING = object()

T = typing.TypeVar('T')

class FieldFlags(typing.TypedDict, total=False):
    init: bool
    repr: bool


class _MetaInfo:
    MISSING = _MISSING
    REQUIRED = REQUIRED

    __slots__ = (
        'alias',
        'desc',
        'validator',
        'serializer',
        'extra',
        '_dataclass_field',
        'name',
        'type',
        'default',
        'default_factory',
        'flags'
    )

    def __init__(
        self,
        *,
        default: typing.Any = _MISSING,
        default_factory:  FactoryFn | typing.Any = _MISSING,
        desc: str | None = None,
        alias: str | None = None,
        validator: ValidatorFn | None = None,
        serializer: SerializerFn | None = None,
        init: bool = True,
        repr: bool = True,
        **extra: typing.Any
    ) -> None:
        if default is REQUIRED:
            default = _MISSING

        if default_factory is REQUIRED:
            default_factory = _MISSING

        self.name = ''
        self.type: typing.Any = typing.Any
        self.alias: str | None = alias
        self.desc: str | None = desc
        self.default: typing.Any = default
        self.default_factory: typing.Any = default_factory
        self.validator: ValidatorFn | None = validator
        self.serializer: SerializerFn | None = serializer
        self.extra: dict[str, typing.Any] = extra
        self.flags: FieldFlags = FieldFlags(
            init=init,
            repr=repr
        )

    def has_default(self) -> bool:
        return self.default is not _MISSING or self.default_factory is not _MISSING

    def produce(self) -> typing.Any:
        if self.default_factory is not _MISSING:
            return self.default_factory()
        return self.default

    def __repr__(self) -> str:
        return (
            f'_MetaInfo(name={self.name!r}, type={self.type!r}, '
            f'default={self.default!r}, default_factory={self.default_factory!r}, '
            f'alias={self.alias!r}, desc={self.desc!r}, flags={self.flags!r})'
        )