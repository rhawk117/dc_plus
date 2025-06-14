"""Internal meta information class for field definitions."""

from __future__ import annotations
from types import EllipsisType
import typing

if typing.TYPE_CHECKING:
    from .types import FactoryFn, ValidatorFn, SerializerFn


REQUIRED = ...
_MISSING = object()

T = typing.TypeVar('T')

class FieldFlags(typing.TypedDict, total=False):
    init: bool
    repr: bool


class MetaField:
    """Internal class for storing field metadata and configuration."""

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
        default_factory: FactoryFn | typing.Any = _MISSING,
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
        '''Check if this field has a default value or factory.

        Returns
        -------
        bool
            _whether a default exists_
        '''
        return self.default is not _MISSING or self.default_factory is not _MISSING

    def produce(self) -> typing.Any:
        '''gets the default value or calls factory function.

        Returns
        -------
        typing.Any
            _the type of the field_
        '''
        if self.default_factory is not _MISSING:
            return self.default_factory()
        return self.default

    def __repr__(self) -> str:
        return (
            f'_MetaField(name={self.name!r}, type={self.type!r}, '
            f'default={self.default!r}, default_factory={self.default_factory!r}, '
            f'alias={self.alias!r}, desc={self.desc!r}, flags={self.flags!r})'
        )


__all__ = ['Meta']

T = typing.TypeVar('T')


def Meta(
    default: T | type[EllipsisType] = _MISSING,
    *,
    default_factory: FactoryFn[T] | type[EllipsisType] | typing.Any = _MISSING,
    alias: str | None = None,
    description: str | None = None,
    validator: ValidatorFn | None = None,
    serializer: SerializerFn | None = None,
    init: bool = True,
    repr: bool = True,
    **extra: typing.Any
) -> typing.Any:
    """Create field metadata for model attributes.

    Parameters
    ----------
    default : T | type[...], optional
        Default value for the field. Use ... (Ellipsis) to mark as required.
    default_factory : FactoryFn[T] | type[...] | None, optional
        Factory function to generate default values.
    alias : str | None, optional
        Alternative name for serialization/deserialization.
    description : str | None, optional
        Human-readable description of the field.
    validator : ValidatorFn | None, optional
        Function to validate field values.
    serializer : SerializerFn | None, optional
        Function to serialize field values.
    init : bool, default=True
        Whether to include this field in the model's __init__ method.
    repr : bool, default=True
        Whether to include this field in the model's __repr__ method.
    **extra : Any
        Additional metadata to store with the field.

    Returns
    -------
    _MetaField
        Field metadata instance for internal use.

    Examples
    --------
    >>> from typing import Annotated
    >>>
    >>> # Modern style with Annotated
    >>> class User(ModelBase):
    ...     name: Annotated[str, Meta(description="User's full name")]
    ...     age: Annotated[int, Meta(default=0)]
    ...
    >>> # Legacy style
    >>> class Product(ModelBase):
    ...     name: str = Meta(default=..., description="Product name")
    ...     price: float = Meta(default=0.0, alias="product_price")
    """
    if default is type(...):
        default = typing.cast(T, REQUIRED)

    if default_factory is ...:
        default_factory = REQUIRED

    return MetaField(
        default=default,
        default_factory=default_factory,
        desc=description,
        alias=alias,
        validator=validator,
        serializer=serializer,
        init=init,
        repr=repr,
        **extra
    )