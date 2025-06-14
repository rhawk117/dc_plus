"""High-performance base model implementation with advanced optimization support."""
from __future__ import annotations

import typing
from collections.abc import Iterator
from functools import lru_cache
from types import MappingProxyType

from .meta import MetaField, _MISSING
from .types import ModelConfig
from .utils.json_adapters import get_json_encoder, get_json_decoder
import typing

if typing.TYPE_CHECKING:
    from typing import Any, ClassVar

__all__ = ['ModelBase']

T = typing.TypeVar('T', bound='ModelBase')

# try to import the optimized cython speedups
try:
    from ._speedups import ( # type: ignore[import]
        fast_getattr,
        fast_setattr,
        fast_validate,
        fast_serialize
    )
    HAVE_C_OPTIMIZED_CODE = True
except ImportError:
    HAVE_C_OPTIMIZED_CODE = False
    fast_getattr = getattr
    fast_setattr = setattr
    fast_validate = lambda v, f: f.validator(v) if f.validator else v
    fast_serialize = lambda v, f: f.serializer(v) if f.serializer else v


def process_model_class(
    cls: type[ModelBase],
    parent_fields: dict[str, MetaField] | None = None
) -> None:
    """Process field definitions and set up model class attributes.

    This function handles the core logic of model class initialization,
    supporting inheritance and configuration merging.
    """

    parent_config = {} # merge parent configuration with current
    getAttr = fast_getattr
    setAttr = fast_setattr
    for base in reversed(cls.__mro__[1:]):
        if issubclass(base, ModelBase) and base is not ModelBase:
            parent_config.update(getAttr(base, 'config', {}))

    current_config = getattr(cls, 'config', {})
    merged_config: dict = {**current_config, **parent_config}

    setAttr(cls, 'config', MappingProxyType(merged_config))

    all_fields = {}
    if parent_fields:
        all_fields.update(parent_fields)

    annotations = getattr(cls, '__annotations__', {})
    getAttr = fast_getattr
    setAttr = fast_setattr
    for name, annotation in annotations.items():
        if name.startswith('_'):
            continue

        field = None
        field_type = annotation

        origin = typing.get_origin(annotation)
        if origin is typing.Annotated:
            args = typing.get_args(annotation)
            field_type = args[0]

            for metadata in args[1:]:
                if isinstance(metadata, MetaField):
                    field = metadata
                    break

        if hasattr(cls, name):
            attr = getAttr(cls, name, None)
            if isinstance(attr, MetaField):
                field = attr
                delattr(cls, name)

        if field is None:
            field = MetaField()

        field.name = name
        field.type = field_type
        all_fields[name] = field

    cls._fields = MappingProxyType(all_fields)
    cls._field_set = frozenset(all_fields.keys())

    _apply_class_optimizations(cls, all_fields, merged_config)


def _apply_class_optimizations(cls: type[ModelBase], fields: dict[str, MetaField], config: dict) -> None:
    if config.get('slots', True) and not hasattr(cls, '__slots__'):
        parent_slots = set()
        for base in cls.__mro__[1:]:
            if hasattr(base, '__slots__'):
                parent_slots.update(base.__slots__)

        new_slots = tuple(name for name in fields if name not in parent_slots)
        if new_slots:
            fast_setattr(cls, '__slots__', new_slots)

    if config.get('init', True):
        fast_setattr(cls, '__init__', _create_optimized_init(cls, fields))

    if config.get('repr', True):
        fast_setattr(cls, '__repr__', _create_optimized_repr(cls, fields))

    if config.get('frozen', False):
        fast_setattr(cls, '__setattr__', _create_frozen_setattr(cls))
        fast_setattr(cls, '__delattr__', _create_frozen_delattr(cls))


def _create_optimized_init(
    cls: type[ModelBase],
    fields: dict[str, MetaField]
) -> typing.Callable:
    setAttr = fast_setattr
    validator = fast_validate
    if HAVE_C_OPTIMIZED_CODE:
        def __init__(self: ModelBase, **kwargs: Any) -> None:
            errors = []
            for name, field in fields.items():
                if not field.flags.get('init', True):
                    continue

                try:
                    if name in kwargs:
                        value = kwargs.pop(name)
                        value = validator(value, field)
                        setAttr(self, name, value)
                    elif field.has_default():
                        setAttr(self, name, field.produce())
                    else:
                        errors.append(name)
                except Exception as e:
                    raise ValueError(f"Error setting field {name}: {e}")

            if errors:
                raise TypeError(f"Missing required fields: {', '.join(errors)}")

            if kwargs:
                raise TypeError(f"Unexpected keyword arguments: {', '.join(kwargs.keys())}")
    else:
        def __init__(self: ModelBase, **kwargs: Any) -> None:
            errors = []
            for name, field in fields.items():
                if not field.flags.get('init', True):
                    continue

                if name in kwargs:
                    value = kwargs.pop(name)
                    if field.validator:
                        value = field.validator(value)
                    setAttr(self, name, value)
                elif field.has_default():
                    setAttr(self, name, field.produce())
                else:
                    errors.append(name)

            if errors:
                raise TypeError(f"Missing required fields: {', '.join(errors)}")

            if kwargs:
                raise TypeError(f"Unexpected keyword arguments: {', '.join(kwargs.keys())}")

    return __init__


def _create_optimized_repr(cls: type[ModelBase], fields: dict[str, MetaField]) -> typing.Callable:
    """Create an optimized __repr__ method."""
    repr_fields = [(name, field) for name, field in fields.items()
                   if field.flags.get('repr', True)]

    getAttr = fast_getattr
    def __repr__(self: ModelBase) -> str:
        parts = []
        for name, _ in repr_fields:
            try:
                value = getAttr(self, name, None)
                parts.append(f"{name}={value!r}")
            except Exception:
                parts.append(f"{name}=<error>")
        return f"{cls.__name__}({', '.join(parts)})"

    return __repr__


def _create_frozen_setattr(cls: type[ModelBase]) -> typing.Callable:
    """Create a __setattr__ that prevents modification after initialization."""
    getAttr = fast_getattr
    def __setattr__(self: ModelBase, name: str, value: Any) -> None:
        if hasattr(self, '_initialized') and getAttr(self, '_initialized'):
            raise AttributeError(f"Cannot modify frozen model {cls.__name__}")
        super(ModelBase, self).__setattr__(name, value)

    return __setattr__


def _create_frozen_delattr(cls: type[ModelBase]) -> typing.Callable:
    """Create a __delattr__ that prevents deletion for frozen models."""
    def __delattr__(self: ModelBase, name: str) -> None:
        raise AttributeError(f"Cannot delete attributes from frozen model {cls.__name__}")

    return __delattr__


@lru_cache(maxsize=128)
def _build_alias_map(fields_items: tuple[tuple[str, MetaField], ...]) -> dict[str, str]:
    """Build and cache alias to field name mapping."""
    alias_map = {}
    for name, field in fields_items:
        if field.alias:
            alias_map[field.alias] = name
    return alias_map


class ModelBase:
    """High-performance base model with serialization and validation capabilities."""

    config: ClassVar[ModelConfig] = typing.cast(ModelConfig, MappingProxyType({}))
    _fields: ClassVar[MappingProxyType[str, MetaField]] = MappingProxyType({})
    _field_set: ClassVar[frozenset[str]] = frozenset()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Process field definitions when subclassing ModelBase."""
        super().__init_subclass__(**kwargs)

        parent_fields = {}
        for base in reversed(cls.__mro__[1:]):
            if issubclass(base, ModelBase) and base is not ModelBase:
                parent_fields.update(dict(base._fields))

        process_model_class(cls, parent_fields)

    def dump(
        self,
        *,
        exclude: set[str] | None = None,
        exclude_none: bool = False,
        dump_by_alias: bool = False
    ) -> dict[str, Any]:
        """Convert model instance to dictionary with advanced serialization options."""
        exclude = exclude or set()
        result = {}

        use_alias = dump_by_alias or self.__class__.config.get('serialize_by_alias', False)
        alias_gen = self.__class__.config.get('alias_generator') if use_alias else None

        getAttr = fast_getattr
        _serializer = fast_serialize
        for name, field in self._fields.items():
            if name in exclude:
                continue

            try:
                value = getAttr(self, name, _MISSING)

                if value is _MISSING:
                    if field.has_default():
                        value = field.produce()
                    else:
                        continue

                if exclude_none and value is None:
                    continue

                if HAVE_C_OPTIMIZED_CODE:
                    value = _serializer(value, field)

                elif field.serializer:
                    value = field.serializer(value)

                if use_alias:
                    key = field.alias or (alias_gen(name) if alias_gen else name)
                else:
                    key = name

                result[key] = value

            except Exception as e:
                if self.__class__.config.get('strict', True):
                    raise
                result[key] = f"<serialization error: {e}>"

        return result

    def as_dict(self) -> dict[str, Any]:
        """Simple, fast conversion to dictionary without options.

        This method provides the fastest path to dictionary conversion,
        bypassing all optional processing for maximum performance.
        """
        getAttr = fast_getattr
        return {
            name: getAttr(self, name, field.produce() if field.has_default() else None)
            for name, field in self._fields.items()
        }

    def json_dumps(
        self,
        *,
        exclude: set[str] | None = None,
        exclude_none: bool = False,
        dump_by_alias: bool = False,
        encoder: str | None = None,
        **json_kwargs: Any
    ) -> str:
        """Convert model to JSON string using optimized encoder."""
        data = self.dump(
            exclude=exclude,
            exclude_none=exclude_none,
            dump_by_alias=dump_by_alias
        )

        encoder_name = encoder or self.__class__.config.get('json_encoder', 'json')
        encoder_func = get_json_encoder(encoder_name)

        return encoder_func(data, **json_kwargs)

    @classmethod
    def load(cls: type[T], data: dict[str, Any], *, strict: bool = True) -> T:
        """Create model instance from dictionary with validation."""
        fields_tuple = tuple(cls._fields.items())
        alias_map = _build_alias_map(fields_tuple)

        kwargs = {}
        errors = []

        for key, value in data.items():
            field_name = alias_map.get(key, key)

            if field_name not in cls._fields:
                if strict:
                    errors.append(f"Unknown field: {key}")
                continue

            field = cls._fields[field_name]

            try:
                if field.validator:
                    value = field.validator(value)
                kwargs[field_name] = value
            except Exception as e:
                errors.append(f"Validation error for {field_name}: {e}")

        if errors and strict:
            raise ValueError(f"Loading errors: {'; '.join(errors)}")

        return cls(**kwargs)

    @classmethod
    def json_loads(cls: type[T], json_str: str, *, decoder: str | None = None, strict: bool = True) -> T:
        """Create model instance from JSON string using optimized decoder."""
        decoder_name = decoder or cls.config.get('json_decoder', 'json')
        decoder_func = get_json_decoder(decoder_name)

        data = decoder_func(json_str)
        return cls.load(data, strict=strict)

    @classmethod
    def meta_fields(
        cls,
        *,
        include: set[str] | None = None,
        exclude: set[str] | None = None
    ) -> Iterator[tuple[str, MetaField]]:
        """Iterate over model fields with filtering options."""
        for name, field in cls._fields.items():
            if include and name not in include:
                continue
            if exclude and name in exclude:
                continue
            yield name, field