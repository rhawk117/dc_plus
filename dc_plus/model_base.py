"""
**model_base.py**

Provides class definition for `ModelBase`, a base class for creating data models and
the `_ModelMeta` metaclass for handling class metadata and typing. Private Utility functions
for dumping and loading models to/from dictionaries and JSON strings are also included, outside
of class definition to avoid expensive refactors.

"""

from typing import Any, ClassVar, Self, TypeVar, dataclass_transform, get_type_hints


from collections.abc import Callable, Generator
import dataclasses
import json

from .metadata import ModelOptions, meta
from . import constant as const


T = TypeVar("T", bound="ModelBase")


def _has_custom_serializer(obj: Any) -> bool:
    """Check if an object has a custom serializer method.

    Parameters
    ----------
    obj : Any
        The object to check for custom serialization capability

    Returns
    -------
    bool
        True if the object's class has a __serialize__ method
    """
    return hasattr(obj.__class__, const.SERIALIZE_METHOD)


def _has_custom_deserializer(target_type: type) -> bool:
    """Check if a type has a custom deserializer method.

    Parameters
    ----------
    target_type : type
        The type to check for custom deserialization capability

    Returns
    -------
    bool
        True if the type has a __deserialize__ method
   """
    return hasattr(target_type, const.DESERIALIZE_METHOD)


def _is_list_type(target_type: type) -> bool:
    """Check if a type annotation represents a list type.

    Parameters
    ----------
    target_type : type
        The type annotation to examine

    Returns
    -------
    bool
        True if the type is a list type annotation
    """
    origin = getattr(target_type, const.ORIGIN_ATTR, None)
    return origin is list


def _get_list_item_type(list_type: type) -> type | None:
    """Extract the item type from a list type annotation.

    Parameters
    ----------
    list_type : type
        The list type annotation (e.g., List[ModelBase])

    Returns
    -------
    type | None
        The item type if available, None otherwise
    """
    args = getattr(list_type, const.ARGS_ATTR, ())
    return args[0] if args else None


@dataclass_transform(
    field_specifiers=(meta,),
    kw_only_default=True
)
class _ModelMeta(type):
    """Metaclass for ModelBase that handles class creation and configuration.

    This metaclass processes ModelOptions, applies dataclass decoration,
    and pre-computes field aliases for optimal runtime performance.

    Class Attributes
    ----------------
    __options__ : ModelOptions
        Confiuration options for the model class
    __custom_flags__ : dict[str, Any]
        Custom configuration flags not used by dataclasses
    __field_aliases__ : dict[str, str]
        Mapping from field names to their aliases
    __reverse_aliases__ : dict[str, str]
        Mapping from aliases back to field names
    """

    __options__: ClassVar[ModelOptions]
    __custom_flags__: ClassVar[dict[str, Any]]
    __field_aliases__: ClassVar[dict[str, str]]
    __reverse_aliases__: ClassVar[dict[str, str]]

    def __new__(
        mcls, name: str, bases: tuple[type, ...], ns: dict[str, Any], **kwargs: Any
    ) -> type["_ModelMeta"]:
        """Create a new ModelBase class with proper configuration.

        Parameters
        ----------
        mcls : type
            The metaclass itself
        name : str
            Name of the class being created
        bases : tuple[type, ...]
            Base classes for the new class
        ns : dict[str, Any]
            Namespace dictionary containing class attributes
        **kwargs : Any
            Additional keyword arguments

        Returns
        -------
        type[_ModelMeta]
            The newly created class with ModelBase capabilities

        Raises
        ------
        TypeError
            If the options attribute is not a ModelOptions instance
        """
        opts = _extract_and_validate_options(ns, name)
        dataclass_kwargs, custom_flags = _separate_options(opts)

        cls = super().__new__(mcls, name, bases, ns, **kwargs)
        _configure_class_attributes(cls, opts, custom_flags)

        cls = dataclasses.dataclass(**dataclass_kwargs)(cls)
        _compute_field_aliases(cls, opts)

        return cls


def _extract_and_validate_options(
    namespace: dict[str, Any],
    class_name: str
) -> ModelOptions:
    """Extract and validate ModelOptions from class namespace.

    Parameters
    ----------
    namespace : dict[str, Any]
        The class namespace dictionary
    class_name : str
        Name of the class being created

    Returns
    -------
    ModelOptions
        The validated options instance

    Raises
    ------
    TypeError
        If options is not a ModelOptions instance
    """
    opts = namespace.pop("options", ModelOptions())

    if not isinstance(opts, ModelOptions):
        raise TypeError(
            const.INVALID_OPTIONS_TYPE.format(class_name=class_name)
        )

    return opts

def _separate_options(opts: ModelOptions) -> tuple[dict[str, Any], dict[str, Any]]:
    """Separate ModelOptions into dataclass kwargs and custom flags.

    Parameters
    ----------
    opts : ModelOptions
        The options instance to process

    Returns
    -------
    tuple[dict[str, Any], dict[str, Any]]
        A tuple of (dataclass_kwargs, custom_flags)
    """
    dataclass_kwargs = {
        k: v
        for k, v in opts.__dict__.items()
        if k in const.DATACLASS_KWARGS and v is not None
    }

    custom_flags = {
        k: v
        for k, v in opts.__dict__.items()
        if k not in const.DATACLASS_KWARGS and v is not None
    }

    return dataclass_kwargs, custom_flags


def _configure_class_attributes(
    cls: type,
    opts: ModelOptions,
    custom_flags: dict[str, Any]
) -> None:
    """Configure class attributes for ModelBase functionality.

    Parameters
    ----------
    cls : type
        The class being configured
    opts : ModelOptions
        The model options
    custom_flags : dict[str, Any]
       Custom configuration flags
    """
    setattr(cls, const.OPTIONS_ATTR, opts)
    setattr(cls, const.CUSTOM_FLAGS_ATTR, custom_flags)


def _compute_field_aliases(cls: type, opts: ModelOptions) -> None:
    """Pre-compute field aliases for runtime performance optimization.

    Parameters
    ----------
    cls : type
        The class to compute aliases for
    opts : ModelOptions
        The model options containing alias generator
    """
    field_aliases = {}
    reverse_aliases = {}

    if opts.serialization_alias_generator:
        for field in dataclasses.fields(cls):
            alias = opts.serialization_alias_generator(field.name)
            if alias != field.name:
                field_aliases[field.name] = alias
                reverse_aliases[alias] = field.name

    setattr(cls, const.FIELD_ALIASES_ATTR, field_aliases)
    setattr(cls, const.REVERSE_ALIASES_ATTR, reverse_aliases)


def _get_model_aliases(model: "ModelBase" | type["ModelBase"]) -> dict[str, str]:
    """Gets the aliases for the model attributes using the configured alias generator.

    Parameters
    ----------
    model : ModelBase | type[ModelBase]
        The model instance or class to get aliases for

    Returns
    -------
    dict[str, str]
        Dictionary mapping field ames to their aliases
    """
    if not model.options.serialization_alias_generator:
        return {}

    aliases = {}
    for field in dataclasses.fields(model):
        alias = model.options.serialization_alias_generator(field.name)
        if alias != field.name:
            aliases[field.name] = alias

    return aliases


def _serialize_value(value: Any, *, dump_by_alias: bool = False) -> Any:
    """Serialize a single value, handling nested models and custom serializers.

    Parameters
    ----------
    value : Any
        The value to serialize
    dump_by_alias : bool, optional
        Whether to use aliases during serialization, by default False

    Returns
    -------
    Any
        The serialized value
    """
    if isinstance(value, ModelBase):
        return value.dump(dump_by_alias=dump_by_alias)

    if isinstance(value, (list, tuple)):
        return [
            _serialize_value(item, dump_by_alias=dump_by_alias)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            k: _serialize_value(v, dump_by_alias=dump_by_alias)
            for k, v in value.items()
        }

    if _has_custom_serializer(value):
        return getattr(value.__class__, const.SERIALIZE_METHOD)(value)

    return value


def _deserialize_value(value: Any, target_type: type | None = None) -> Any:
    """Deserialize a single value, handling nested models and custom deserializers.

    Parameters
    ----------
    value : Any
        The value to deserialize
    target_type : type | None, optional
        The expected type for the deserialized value, by default None

    Returns
    -------
    Any
        The deserialized value
    """
    if not target_type:
        return value

    if _is_nested_model(value, target_type):
        return target_type.load(value)

    if _has_custom_deserializer(target_type) and isinstance(value, dict):
        return getattr(target_type, const.DESERIALIZE_METHOD)(value)

    if _is_list_type(target_type) and isinstance(value, list):
        return _deserialize_list(value, target_type)

    return value


def _is_nested_model(value: Any, target_type: type) -> bool:
    """Check if a value should be deserialized as a nested model.

    Parameters
    ----------
    value : Any
        The value to check    target_type : type
        The target type for deserialization

    Returns
    -------
    bool
        True if the value should be deserialized as a nested model
    """
    return (
        isinstance(value, dict)
        and isinstance(target_type, type)
        and issubclass(target_type, ModelBase)
    )


def _deserialize_list(value: list, list_type: type) -> list:
    """Deserialize a list with typed items.

    Parameters
    ----------
    value : list
        The list to deserialize
    list_type : type
        The list type annotation

    Returns
    -------
    list
        The deserialized list
    """
    item_type = _get_list_item_type(list_type)
    if not item_type:
        return value

    return [_deserialize_value(item, item_type) for item in value]


def _asdict_iterator(
    model: "ModelBase",
    *,
    exclude_attrs: set[str] | None = None,
    exclude_none: bool = False,    dump_by_alias: bool = False,
    dict_factory: Callable[[list[tuple[str, Any]]], dict[str, Any]] = dict,
) -> Generator[tuple[str, Any], None, None]:
    """Create a dictionary factory for the model.

    Parameters
    ----------
    model : ModelBase
        The model instance to serialize
    exclude_attrs : set[str] | None, optional
        Set of attribute names to exclude from serialization, by default None
    exclude_none : bool, optional
        Whether to exclude None values from serialization, by default False
    dump_by_alias : bool, optional
        Whether to use field aliases as keys, by default False
    dict_factory : Callable, optional
        Factory function for creating dictionaries, by default dict

    Yields
    ------
    tuple[str, Any]
        Key-value pairs for the serialized model

    Raises
    ------
    ValueError
        If dump_by_alias is True but no alias generator is configured
    """
    if dump_by_alias and not model.options.serialization_alias_generator:
        raise ValueError(
            const.ALIAS_GENERATOR_MISSING.format(flag_name="dump_by_alias")
        )

    for field in dataclasses.fields(model):
        if _should_exclude_field(field.name, exclude_attrs):
            continue

        value = getattr(model, field.name)

        if _should_exclude_none_value(value, exclude_none):
            continue
        serialized_value = _serialize_value(value, dump_by_alias=dump_by_alias)
        key = _get_serialization_key(field.name, model, dump_by_alias)

        yield key, serialized_value


def _should_exclude_field(field_name: str, exclude_attrs: set[str] | None) -> bool:
    """Check if a field should be excluded from serialization.

    Parameters
    ----------
    field_name : str
        The name of the field
    exclude_attrs : set[str] | None
        Set of attributes to exclude

    Returns
    -------
    bool
        True if the field should be excluded
    """
    return exclude_attrs is not None and field_name in exclude_attrs


def _should_exclude_none_value(value: Any, exclude_none: bool) -> bool:
    """Check if a None value should be excluded from serialization.

    Parameters
    ----------
    value : Any
        The field value
    exclude_none : bool
        Whether to exclude None values

    Returns
    -------
    bool
        True if the value should be excluded
    """
    return exclude_none and value is None

def _get_serialization_key(
    field_name: str, model: "ModelBase", dump_by_alias: bool
) -> str:
    """Get the key to use for serialization (either field name or alias).

    Parameters
    ----------
    field_name : str
        The original field name
    model : ModelBase
        The model instance
    dump_by_alias : bool
        Whether to use aliases

    Returns
    -------
    str
        The key to use for serialization
    """
    if not dump_by_alias or not model.options.serialization_alias_generator:
        return field_name

    return model.options.serialization_alias_generator(field_name)


def _prepare_loaded_dict(
    model: type["ModelBase"], *, model_dict: dict[str, Any], load_by_alias: bool = False
) -> dict[str, Any]:
    """Prepare dictionary for loading, handling alias resolution and nested model deserialization.

    Parameters
    ----------
    model : type[ModelBase]
        The model class being loaded
    model_dict : dict[str, Any]
        The dictionary data to prepare
    load_by_alias : bool, optional
        Whether to resolve aliases to field names, by default False

    Returns
    -------
    dict[str, Any]        The prepared dictionary ready for model instantiation

    Raises
    ------
    ValueError
        If load_by_alias is True but no alias generator is configured
    """
    if load_by_alias and not model.options.serialization_alias_generator:
        raise ValueError(
            const.ALIAS_GENERATOR_MISSING.format(flag_name="load_by_alias")
        )

    working_dict = dict(model_dict)
    _resolve_aliases_if_needed(model, working_dict, load_by_alias)
    _deserialize_nested_models(model, working_dict)

    return working_dict


def _resolve_aliases_if_needed(
    model: type["ModelBase"], working_dict: dict[str, Any], load_by_alias: bool
) -> None:
    """Resolve field aliases to actual field names in the working dictionary.

    Parameters
    ----------
    model : type[ModelBase]
        The model class
    working_dict : dict[str, Any]
        The dictionary to modify in place
    load_by_alias : bool
        Whether alias resolution should be performed
    """
    if not load_by_alias or not model.options.serialization_alias_generator:
        return

    alias_list = _get_model_aliases(model)
    for field_name, alias in alias_list.items():
        if alias in working_dict and field_name not in working_dict:
            working_dict[field_name] = working_dict.pop(alias)

def _deserialize_nested_models(
    model: type["ModelBase"],
    working_dict: dict[str, Any]
) -> None:
    """Deserialize nested models within the dictionary data.

    Parameters
    ----------
    model : type[ModelBase]
        The model class being loaded
    working_dict : dict[str, Any]
        The dictionary to modify in place
    """
    try:
        type_hints = get_type_hints(model)

        for field_name, value in working_dict.items():
            if field_name in type_hints:
                target_type = type_hints[field_name]
                working_dict[field_name] = _deserialize_value(value, target_type)

    except (ImportError, AttributeError):
        # Gracefully handle cases where type inspection fails
        pass


class ModelBase(metaclass=_ModelMeta):
    """Base class for creating high-performance data models with serialization capabilities.

    ModelBase provides a lightweight alternative to Pydantic with focus on performance
    and minimal dependencies. It uses Python's dataclasses under the hood while adding
    advanced serialization, deserialization, and nested model support.

    Attributes
    ----------
    options : ModelOptions
        Configuration options for the model behavior

    Examples
    --------
    Basic model definition:

    >>> from dataclasses importdataclass
    >>> from typing import Optional
    >>>
    >>> class User(ModelBase):
    ...     name: str
    ...     age: int
    ...     email: Optional[str] = None
    >>>
    >>> user = User(name="Alice", age=30, email="alice@example.com")
    >>> user.dump()
    {'name': 'Alice', 'age': 30, 'email': 'alice@example.com'}

    Model with custom options:

    >>> def camel_case(name: str) -> str:
    ...     components = name.split('_')
    ...     return components[0] + ''.join(x.capitalize() for x in components[1:])
    >>>
    >>> class APIResponse(ModelBase):
    ...     options = ModelOptions(
    ...         serialization_alias_generator=camel_case,
    ...         exclude_none=True
    ...     )
    ...
    ...     user_id: int
    ...     full_name: str
    ...     middle_name: Optional[str] = None
    >>>
    >>> response = APIResponse(user_id=123, full_name="John Doe")
    >>> response.dump(dump_by_alias=True)
    {'userId': 123, 'fullName': 'John Doe'}

    Nested models:

    >>> class Address(ModelBase):
    ...     street: str
    ...     city: str
    ...     country: str
    >>>
    >>> class Person(ModelBase):
    ...     name: str
    ...     address: Address    >>>
    >>> person_data = {
    ...     'name': 'Bob',
    ...     'address': {'street': '123 Main St', 'city': 'Boston', 'country': 'USA'}
    ... }
    >>> person = Person.load(person_data)
    >>> isinstance(person.address, Address)
    True
    """

    options: ModelOptions = ModelOptions()

    def dump(
        self,
        *,
        exclude_attrs: set[str] | None = None,
        exclude_none: bool = False,
        dump_by_alias: bool = False,
        dict_factory: Callable[[list[tuple[str, Any]]], dict[str, Any]] = dict,
    ) -> dict[str, Any]:
        """Dump the model to a dictionary.

        Parameters
        ----------
        exclude_attrs : set[str] | None, optional
            Set of attribute names to exclude from the output, by default None
        exclude_none : bool, optional
            Whether to exclude attributes with None values, by default False
        dump_by_alias : bool, optional
            Whether to use field aliases as dictionary keys, by default False
        dict_factory : Callable, optional
            Factory function for creating the output dictionary, by default dict

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the model

        Raises
        ------
        ValueError
            If dump_by_alias is Tru but no alias generator is configured

        Examples
        --------
        >>> user = User(name="Alice", age=30, email=None)
        >>> user.dump()
        {'name': 'Alice', 'age': 30, 'email': None}
        >>> user.dump(exclude_none=True)
        {'name': 'Alice', 'age': 30}
        >>> user.dump(exclude_attrs={'email'})
        {'name': 'Alice', 'age': 30}
        """
        return dict(
            _asdict_iterator(
                self,
                exclude_attrs=exclude_attrs,
                exclude_none=exclude_none,
                dump_by_alias=dump_by_alias,
                dict_factory=dict_factory,
            )
        )

    def json_dumps(
        self,
        *,
        exclude_attrs: set[str] | None = None,
        exclude_none: bool = False,
        dump_by_alias: bool = False,
        dict_factory: Callable[[list[tuple[str, Any]]], dict[str, Any]] = dict,
        **json_dumps_kwargs: Any,
    ) -> str:
        """Dump the model to a JSON string.

        Parameters
        ----------
        exclude_attrs : set[str] | None, optional
            Set of attribute names to exclude from the output, by default None
        exclude_none : bool, optional
            Whether to exclude attributes with None values, by default False
        dump_by_alias : bool, optional
            Whether to use field aliases as dictionary keys, by default False
        dict_factory : Callable, optional            Factory function for creating the intermediate dictionary, by default dict
        **json_dumps_kwargs : Any
            Additional keyword arguments passed to json.dumps()

        Returns
        -------
        str
            JSON string representation of the model

        Examples
        --------
        >>> user = User(name="Alice", age=30)
        >>> user.json_dumps()
        '{"name": "Alice", "age": 30, "email": null}'
        >>> user.json_dumps(indent=2)
        '{\\n  "name": "Alice",\\n  "age": 30,\\n  "email": null\\n}'
        """
        dumped = self.dump(
            exclude_attrs=exclude_attrs,
            exclude_none=exclude_none,
            dump_by_alias=dump_by_alias,
            dict_factory=dict_factory
        )
        return json.dumps(dumped, **json_dumps_kwargs)

    @classmethod
    def load(
        cls,
        model_dict: dict[str, Any],
        *,
        load_by_alias: bool = False,
    ) -> Self:
        """Load the model from a dictionary.

        Parameters
        ----------
        model_dict : dict[str, Any]
            The dictionary to load the model from
        load_by_alias : bool, optional
            Whether to resolve alias names to proper attribute names, by default False

        Returns        -------
        Self
            New instance of the model class

        Raises
        ------
        ValueError
            If load_by_alias is True but no alias generator is configured
        TypeError
            If the dictionary contains invalid data for model creation

        Examples
        --------
        >>> data = {'name': 'Bob', 'age': 25, 'email': 'bob@example.com'}
        >>> user = User.load(data)
        >>> user.name
        'Bob'

        Loading with aliases:
        >>> class APIResponse(ModelBase):
        ...     options = ModelOptions(
        ...         serialization_alias_generator=alias_generator.camel_case
        ...     )
        >>> api_data = {'userId': 123, 'fullName': 'Jane Doe'}
        >>> response = APIResponse.load(api_data, load_by_alias=True)
        >>> response.user_id
        123
        """
        try:
            model_kwargs = _prepare_loaded_dict(
                cls,
                model_dict=model_dict,
                load_by_alias=load_by_alias
            )
            return cls(**model_kwargs)
        except TypeError as e:
            raise TypeError(
                const.MODEL_CREATION_ERROR.format(class_name=cls.__name__, error=e)
            )

    @classmethod
    def json_loads(
        cls,
        json_str: str | bytes | bytearray,
        *,
        load_by_alias: bool = False,
        **json_loads_kwargs: Any
    ) -> Self:
        """Load the model from a JSON string.

        Parameters
        ----------
        json_str : str | bytes | bytearray
            The JSON string to parse and load
        load_by_alias : bool, optional
            Whether to resolve alias names to proper attributes, by default False
        **json_loads_kwargs : Any
            Additional keyword arguments passed to json.loads()

        Returns
        -------
        Self
            New instance of the model class

        Raises
        ------
        ValueError
            If the JSON string is invalid or load_by_alias configuration is incorrect
        TypeError
            If the parsed JSON contains invalid data for model creation

        Examples
        --------
        >>> json_data = '{"name": "Charlie", "age": 35, "email": "charlie@example.com"}'
        >>> user = User.json_loads(json_data)
        >>> user.age
        35

        Loading from bytes:
        >>> byte_data = b'{"name": "David", "age": 40}'
        >>> user = User.json_loads(byte_data)
        >>> user.name
        'David'
        """
        if isinstance(json_str, (bytes, bytearray)):
            json_str = json_str.decode(const.DEFAULT_ENCODING)

        try:
            model_dict = json.loads(json_str, **json_loads_kwargs)
        except json.JSONDecodeError as e:
            raise ValueError(const.JSON_DECODE_ERROR.format(error=e))

        return cls.load(model_dict, load_by_alias=load_by_alias)

    def items(
        self,
        *,
        exclude_attrs: set[str] | None = None,
        exclude_none: bool = False,
        use_aliases: bool = False,
        dict_factory: Callable[[list[tuple[str, Any]]], dict[str, Any]] = dict,
    ) -> Generator[tuple[str, Any], None, None]:
        """Iterator over the model's attributes as key-value pairs.

        Parameters
        ----------
        exclude_attrs : set[str] | None, optional
            Set of attribute names to exclude (use actual field names, not aliases), by default None
        exclude_none : bool, optional
            Whether to exclude attributes with None values, by default False
        use_aliases : bool, optional
            Whether to use alias names from serialization_alias_generator for keys, by default False
        dict_factory : Callable, optional
            Factory function for creating intermediate dictionaries, by default dict

        Yields
        ------
        Generator[tuple[str, Any], None, None]
            Key-value pairs of (attribute_name, attribute_value)

        Raises
        ------
        ValueError
            If use_aliases is True but no alias generator is configured

        Examples        --------
        >>> user = User(name="Eve", age=28, email=None)
        >>> list(user.items())
        [('name', 'Eve'), ('age', 28), ('email', None)]
        >>> list(user.items(exclude_none=True))
        [('name', 'Eve'), ('age', 28)]
        >>> list(user.items(exclude_attrs={'email'}))
        [('name', 'Eve'), ('age', 28)]
        """
        yield from _asdict_iterator(
            self,
            exclude_attrs=exclude_attrs,
            exclude_none=exclude_none,
            dump_by_alias=use_aliases,
            dict_factory=dict_factory
        )

    def as_dict(self) -> dict[str, Any]:
        """Convert the model to a dictionary without any processing overhead.

        This method provides the fastest dictionary conversion by directly
        using dataclasses.asdict() without additional processing like alias
        resolution or nested model serialization.

        Returns
        -------
        dict[str, Any]
            Raw dictionary representation of the model

        Examples
        --------
        >>> user = User(name="Frank", age=45, email="frank@example.com")
        >>> user.as_dict()
        {'name': 'Frank', 'age': 45, 'email': 'frank@example.com'}
        """
        return dataclasses.asdict(self)

    @classmethod
    def register_serializer(
        cls, target_type: type, serializer: Callable[[Any], Any]
    ) -> None:
        """Register a custom seralizer for a specific type.

        The serializer function will be called during model serialization
        whenever an instance of the target type is encountered.

        Parameters
        ----------
        target_type : type
            The type to register the serializer for
        serializer : Callable[[Any], Any]
            Function that takes an instance and returns serializable data

        Examples
        --------
        >>> from datetime import datetime
        >>> def serialize_datetime(dt: datetime) -> str:
        ...     return dt.isoformat()
        >>>
        >>> ModelBase.register_serializer(datetime, serialize_datetime)
        >>>
        >>> class Event(ModelBase):
        ...     name: str
        ...     timestamp: datetime
        >>>
        >>> event = Event(name="Meeting", timestamp=datetime(2024, 1, 15, 10, 30))
        >>> event.dump()
        {'name': 'Meeting', 'timestamp': '2024-01-15T10:30:00'}
        """
        setattr(target_type, const.SERIALIZE_METHOD, staticmethod(serializer))

    @classmethod
    def register_deserializer(
        cls,
        target_type: type,
        deserializer: Callable[[Any], Any]
    ) -> None:
        """Register a custom deserializer for a specific type.

        The deserializer function will be called during model loading
        whenever serialized data needs to be converted to the target type.

        Parameters
        ----------
        target_type : type
        The type to register the deserializer for
        deserializer : Callable[[Any], Any]
            Function that takes serialized data and returns an instance

        Examples
        --------
        >>> from datetime import datetime
        >>> def deserialize_datetime(iso_string: str) -> datetime:
        ...     return datetime.fromisoformat(iso_string)
        >>>
        >>> ModelBase.register_deserializer(datetime, deserialize_datetime)
        >>>
        >>> data = {'name': 'Meeting', 'timestamp': '2024-01-15T10:30:00'}
        >>> class Event(ModelBase):
        ...     name: str
        ...     timestamp: datetime
        >>> event = Event.load(data)
        >>> isinstance(event.timestamp, datetime)
        True
        """
        setattr(target_type, const.DESERIALIZE_METHOD, staticmethod(deserializer))

