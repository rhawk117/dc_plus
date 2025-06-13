"""
**meta_data.py**

Provides a wrapper around `dataclasses.field` to add metadata and extended functionality
to the fields of a dataclass. This allows for additional attributes like default values,
descriptions, and custom configuration options for ModelBase classes.

"""
from __future__ import annotations

import dataclasses
from typing import Any, TypeVar
from collections.abc import Callable, Mapping


T = TypeVar("T")


def meta(
    *,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[[], Any] | None = None,
    desc: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    **dataclass_kwargs: Any
) -> dataclasses.Field:
    """A wrapper around `dataclasses.field` that allows you to add
    additional metadata to the field with extended functionality.

    This function provides enhanced field definition capabilities for ModelBase
    classes, allowing developers to attach descriptive information and custom
    metadata to model fields while maintaining full compatibility with the
    standard dataclasses.field() function.

    Parameters
    ----------
    default : Any, optional
        Default value for the field. If not provided, the field is considered
        required and must be specified during model instantiation, by default dataclasses.MISSING
    default_factory : Callable[[], Any] | None, optional
        Factory function that will be called to generate the default value.
        This is useful for mutable default values like lists or dictionaries, by default None
    desc : str | None, optional
        Human-readable description of the field's purpose and expected content.
        This description can be used for documentation generation or validation
        error messages, by default None
    metadata : Mapping[str, Any] | None, optional
        Additional metadata dictionary that will be attached to the field.
        This can contain any custom information needed by the application, by default None
    **dataclass_kwargs : Any
        Additional keyword arguments that will be passed directly to the
        underlying dataclasses.field() function, allowing access to all
        standard dataclass field options

    Returns
    -------
    dataclasses.Field
        Enhanced dataclass field with additional metadata capabilities

    Examples
    --------
    Basic field with description:

    >>> class Product(ModelBase):
    ...     name: str = meta(desc="Product name as displayed to customers")
    ...     price: float = meta(desc="Price in USD, must be positive")
    ...     category: str = meta(default="general", desc="Product category for organization")

    Field with default factory for mutable types:

    >>> class ShoppingCart(ModelBase):
    ...     items: list[str] = meta(
    ...         default_factory=list,
    ...         desc="List of product IDs in the cart"
    ...     )
    ...     metadata: dict[str, Any] = meta(
    ...         default_factory=dict,
    ...         desc="Additional cart metadata"
    ...     )

    Field with custom metadata:

    >>> class DatabaseModel(ModelBase):
    ...     id: int = meta(
    ...         desc="Primary key identifier",
    ...         metadata={"db_column": "id", "db_type": "INTEGER PRIMARY KEY"}
    ...     )
    ...     created_at: str = meta(
    ...         desc="Creation timestamp in ISO format",
    ...         metadata={"db_column": "created_at", "db_type": "TIMESTAMP"}
    ...     )

    Field with dataclass-specific options:

    >>> class InternalModel(ModelBase):
    ...     public_field: str = meta(desc="This field appears in repr")
    ...     private_field: str = meta(
    ...         desc="This field is hidden from repr",
    ...         repr=False
    ...     )
    ...     computed_field: str = meta(
    ...         desc="This field is not included in initialization",
    ...         init=False,
    ...         default="computed_value"
    ...     )
    """
    enhanced_metadata = dict(metadata or {})

    if desc is not None:
        enhanced_metadata["desc"] = desc

    return dataclasses.field(
        default=default,
        default_factory=default_factory,  # type: ignore[arg-type]
        metadata=enhanced_metadata,
        **dataclass_kwargs
    )


@dataclasses.dataclass(slots=True, frozen=True)
class ModelOptions:
    """Configurations options for ModelBase classes, defining how they behave
    during instantiation, serialization, and deserialization.

    ModelOptions provides comprehensive control over how ModelBase classes are
    constructed and how they handle serialization and deserialization operations.
    The class is designed to be immutable (frozen) and memory-efficient (slots)
    to minimize runtime overhead.

    Attributes
    ----------
    frozen : bool | None, optional
        Controls whether instances of the model are immutable after creation.
        When set to True, attempting to modify any field after instantiation
        will raise a FrozenInstanceError. This is useful for creating value
        objects or ensuring data integrity in concurrent environments.
        When None, the dataclass default behavior is used, by default None

    slots : bool | None, optional
        Determines whether to use __slots__ for memory optimization.
        When True, instances will use less memory and have faster attribute
        access, but dynamic attribute assignment will be disabled. This is
        recommended for models with many instances or performance-critical
        applications. When None, the dataclass default is used, by default None

    order : bool | None, optional
        Enables automatic generation of comparison methods (__lt__, __le__,
        __gt__, __ge__) based on field order. When True, instances can be
        sorted and compared using standard comparison operators. The comparison
        is performed field-by-field in the order they are defined in the class.
        When None, no comparison methods are generated, by default None

    kw_only : bool | None, optional
        Forces all fields to be keyword-only arguments in the generated
        __init__ method. When True, instances must be created using named
        arguments (e.g., Model(name="value")) rather than positional arguments.
        This improves code readability and reduces errors from argument
        reordering. When None, fields can be positional or keyword, by default None

    exclude_none : bool, optional
        Default behavior for excluding None values during serialization.
        When True, fields with None values will be omitted from the output
        of dump() and json_dumps() methods unless explicitly overridden.
        This is useful for creating clean API responses and reducing payload
        size. Can be overridden per serialization call, by default False

    serialization_alias_generator : Callable[[str], str] | None, optional
        Function that transforms field names into alternative representations
        for serialization. The function receives the original field name as
        input and should return the desired alias. Common use cases include
        converting snake_case to camelCase for JSON APIs or applying naming
        conventions required by external systems. When None, field names
        are used as-is during serialization, by default None

    Examples
    --------
    Basic model with immutable instances:

    >>> class ImmutableUser(ModelBase):
    ...     options = ModelOptions(frozen=True)
    ...
    ...     name: str
    ...     email: str
    ...     created_at: str
    >>>
    >>> user = ImmutableUser(name="Alice", email="alice@example.com", created_at="2024-01-01")
    >>> # user.name = "Bob"  # This would raise FrozenInstanceError

    Memory-optimized model with slots:

    >>> class OptimizedProduct(ModelBase):
    ...     options = ModelOptions(slots=True, kw_only=True)
    ...
    ...     id: int
    ...     name: str
    ...     price: float
    ...     category: str
    >>>
    >>> # Must use keyword arguments due to kw_only=True
    >>> product = OptimizedProduct(id=1, name="Widget", price=9.99, category="tools")

    Model with custom serialization aliases:

    >>> def to_camel_case(snake_str: str) -> str:
    ...     components = snake_str.split('_')
    ...     return components[0] + ''.join(x.capitalize() for x in components[1:])
    >>>
    >>> class APIModel(ModelBase):
    ...     options = ModelOptions(
    ...         serialization_alias_generator=to_camel_case,
    ...         exclude_none=True
    ...     )
    ...
    ...     user_id: int
    ...     full_name: str
    ...     middle_name: str | None = None
    ...     last_login: str | None = None
    >>>
    >>> model = APIModel(user_id=123, full_name="John Doe")
    >>> model.dump(dump_by_alias=True)
    {'userId': 123, 'fullName': 'John Doe'}

    Sortable model with comparison methods:

    >>> class Priority(ModelBase):
    ...     options = ModelOptions(order=True, frozen=True)
    ...
    ...     level: int
    ...     description: str
    >>>
    >>> high = Priority(level=1, description="High priority")
    >>> medium = Priority(level=2, description="Medium priority")
    >>> low = Priority(level=3, description="Low priority")
    >>>
    >>> sorted([low, high, medium])
    [Priority(level=1, description='High priority'),
     Priority(level=2, description='Medium priority'),
     Priority(level=3, description='Low priority')]

    Enterprise model with comprehensive configuration:

    >>> class EnterpriseModel(ModelBase):
    ...     options = ModelOptions(
    ...         frozen=True,          # Immutable for thread safety
    ...         slots=True,           # Memory optimization
    ...         kw_only=True,         # Explicit field naming
    ...         order=True,           # Enable sorting
    ...         exclude_none=True,    # Clean serialization
    ...         serialization_alias_generator=to_camel_case
    ...     )
    ...
    ...     record_id: int
    ...     created_by: str
    ...     last_modified: str | None = None
    ...     metadata: dict[str, Any] = meta(default_factory=dict)
    """

    frozen: bool | None = None
    slots: bool | None = None
    order: bool | None = None
    kw_only: bool | None = None
    exclude_none: bool = False
    serialization_alias_generator: Callable[[str], str] | None = None
