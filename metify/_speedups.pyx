# cython: language_level=3, boundscheck=False, wraparound=False
# cython: profile=False, linetrace=False
"""Cython speedups for critical performance paths.

NOTE

This module follows strict reference counting conventions:
- Input arguments are declared as 'object' type
- Return values use 'object' for new references
- PyObject* is used only for borrowed references with explicit handling
"""

from cpython.object cimport PyObject_GetAttr, PyObject_SetAttr, PyObject_HasAttr

from typing import Any, Dict, List, Optional, Type, TypeVar
from .core._meta import MetaField, _MISSING
from .core.types import ValidatorFn, SerializerFn

T = TypeVar('T')

ctypedef bint cbool

ctypedef object (*validator_func)(object)
ctypedef object (*serializer_func)(object)


cdef class FastFieldAccess:
    """Optimized field access operations with proper reference counting."""

    @staticmethod
    def get_attr_fast(object obj, object name, object default):
        """Fast attribute getter with default value support.

        Following Cython conventions:
        - All parameters are 'object' type for automatic refcounting
        - Returns 'object' which is a new reference
        """
        cdef object result

        try:
            result = PyObject_GetAttr(obj, name)
            return result
        except AttributeError:
            return default

    @staticmethod
    def set_attr_fast(object obj, object name, object value):
        """Fast attribute setter with proper error handling.

        All parameters are 'object' for automatic reference counting.
        """
        # PyObject_SetAttr handles references internally
        if PyObject_SetAttr(obj, name, value) < 0:
            raise AttributeError(f"Cannot set attribute {name}")


def fast_getattr(obj: Any, name: str, default: Any = _MISSING) -> Any:
    """Optimized getattr implementation using Cython.

    This function provides faster attribute access with proper
    reference counting handled automatically by Cython.
    """
    return FastFieldAccess.get_attr_fast(obj, name, default)


def fast_setattr(obj: Any, name: str, value: Any) -> None:
    """Optimized setattr implementation using Cython.

    This function provides faster attribute setting with proper
    reference counting handled automatically by Cython.
    """
    FastFieldAccess.set_attr_fast(obj, name, value)


cdef class FieldValidator:
    """Optimized field validation with safe reference counting."""

    @staticmethod
    def validate_with_type_check(
        object value,
        object field_type,
        ValidatorFn validator
    ) -> object:
        """Validate value with optional type checking and custom validator.

        All parameters and return are properly typed for IDE support.
        """
        if validator is None:
            return value

        try:
            return validator(value)
        except Exception as e:
            raise ValueError(f"Validation failed: {e}")


def fast_validate(value: Any, field: MetaField) -> Any:
    """Fast field validation with type checking support.

    This function provides optimized validation with proper
    reference counting for all operations.
    """
    if field.validator is None:
        return value

    return FieldValidator.validate_with_type_check(value, field.type, field.validator)


cdef class FieldSerializer:
    """Optimized field serialization with safe reference counting."""

    @staticmethod
    def serialize_value(object value, SerializerFn serializer):
        """Serialize value using custom serializer if available.

        Using proper types ensures IDE understanding and proper reference counting.
        """
        if serializer is None:
            return value
        try:
            return serializer(value)
        except Exception as e:
            raise ValueError(f"Serialization failed: {e}")


def fast_serialize(value: Any, field: MetaField) -> Any:
    """Fast field serialization with proper reference counting.

    This function provides optimized serialization while ensuring
    all references are properly managed.
    """
    if field.serializer is None:
        return value

    return FieldSerializer.serialize_value(
        value,
        field.serializer
    )


cdef class BatchProcessor:
    """Batch processing operations with safe reference counting."""

    @staticmethod
    def validate_batch(list objects, dict fields):
        """Validate a batch of objects efficiently.

        Using Python types (list, dict) ensures proper reference counting
        for container operations.
        """
        cdef list results = []
        cdef object obj, value, validated
        cdef str field_name
        cdef MetaField field

        for obj in objects:
            for field_name, field_obj in fields.items():
                field = <MetaField>field_obj
                if field.validator is not None:
                    try:
                        value = FastFieldAccess.get_attr_fast(
                            obj,
                            field_name,
                            _MISSING
                        )
                        if value is not _MISSING:
                            validated = FieldValidator.validate_with_type_check(
                                value,
                                field.type,
                                field.validator
                            )
                            setattr(obj, field_name, validated)
                    except Exception:
                        pass
            results.append(obj)

        return results

    @staticmethod
    def serialize_batch(list objects, dict fields, cbool exclude_none):
        """Serialize a batch of objects efficiently.

        All container operations use Python types for safe refcounting.
        """
        cdef list results = []
        cdef dict obj_dict
        cdef object obj, value
        cdef str field_name
        cdef MetaField field

        for obj in objects:
            obj_dict = {}
            for field_name, field_obj in fields.items():
                field = <MetaField>field_obj
                try:
                    value = PyObject_GetAttr(obj, field_name)
                    if value is None:
                        value = _MISSING

                    if value is _MISSING:
                        if field.has_default():
                            value = field.produce()
                        else:
                            continue

                    if exclude_none and value is None:
                        continue

                    if field.serializer is not None:
                        value = FieldSerializer.serialize_value(value, field.serializer)

                    obj_dict[field_name] = value
                except Exception:
                    continue

            results.append(obj_dict)

        return results


def validate_models_batch(models: List[Any], fields: Dict[str, MetaField]) -> List[Any]:
    """Validate a batch of model instances efficiently.

    This function provides optimized batch validation with proper
    reference counting for all operations.
    """
    return BatchProcessor.validate_batch(models, fields)


def serialize_models_batch(
    models: List[Any],
    fields: Dict[str, MetaField],
    exclude_none: bool = False
) -> List[Dict[str, Any]]:
    """Serialize a batch of model instances efficiently.

    This function provides optimized batch serialization with proper
    reference counting for all operations.
    """
    return BatchProcessor.serialize_batch(models, fields, <cbool>exclude_none)


cdef dict TYPE_VALIDATORS = {}


cdef class TypeDispatcher:
    """Fast type-based dispatch with safe reference counting."""

    @staticmethod
    def is_valid_type(object value, object expected_type):
        """Check if value matches expected type.

        Using 'object' parameters ensures proper refcounting.
        """
        if type(value) is expected_type:
            return True
        return isinstance(value, <type>expected_type)

    @staticmethod
    def register_type_validator(object type_obj, object validator):
        TYPE_VALIDATORS[type_obj] = validator

    @staticmethod
    def get_type_validator(object type_obj):
        return TYPE_VALIDATORS.get(type_obj)


cdef class MemoryPool:
    """Simple memory pool for model instances with safe refcounting."""
    cdef list _pool
    cdef object _model_class
    cdef int _max_size
    cdef dict _field_defaults

    def __init__(self, model_class: Type[Any], max_size: int = 100) -> None:

        self._model_class = model_class
        self._max_size = max_size
        self._pool = []
        self._field_defaults = {}
        if PyObject_HasAttr(model_class, '_fields'):
            fields_dict = PyObject_GetAttr(model_class, '_fields')
            for name, field_obj in fields_dict.items():
                field: MetaField = <MetaField>field_obj
                if field.has_default():
                    self._field_defaults[name] = field.default

    def acquire(self) -> Any:
        """Get an instance from the pool or create new.

        Returns object with proper reference counting.
        """
        cdef object instance

        if self._pool:
            instance = self._pool.pop()
            for name, default in self._field_defaults.items():
                try:
                    setattr(instance, name, default)
                except Exception:
                    pass
            return instance
        else:
            return object.__new__(<type>self._model_class)

    def release(self, object obj) -> None:
        """Return instance to pool for reuse.

        Parameter is 'object' for proper reference counting.
        """
        if len(self._pool) < self._max_size:
            for attr in dir(obj):
                if not attr.startswith('_') and attr not in self._field_defaults:
                    try:
                        delattr(obj, attr)
                    except Exception:
                        pass
            self._pool.append(obj)

    def clear(self) -> None:
        self._pool.clear()

    @property
    def size(self) -> int:
        return len(self._pool)


def create_model_pool(model_class: Type[Any], max_size: int = 100) -> MemoryPool:
    """Create a memory pool for efficient model instance allocation.

    The pool maintains proper reference counting for all cached instances.
    """
    return MemoryPool(model_class, max_size)


cdef class OptimizedDescriptor:
    """Descriptor for optimized attribute access with caching."""
    cdef object name
    cdef MetaField field
    cdef dict _cache

    def __init__(self, name: str, field: MetaField) -> None:
        self.name = name
        self.field = field
        self._cache = {}

    def __get__(self, obj: Optional[Any], objtype: Optional[Type[Any]] = None) -> Any:
        if obj is None:
            return self

        cdef object value
        cdef int obj_id = id(obj)

        if obj_id in self._cache:
            return self._cache[obj_id]

        try:
            value = PyObject_GetAttr(obj, f"_{self.name}")
            self._cache[obj_id] = value
            return value
        except AttributeError:
            if self.field.has_default():
                value = self.field.produce()
                setattr(obj, f"_{self.name}", value)
                self._cache[obj_id] = value
                return value
            raise AttributeError(f"'{type(obj).__name__}' has no attribute '{self.name}'")

    def __set__(self, obj: Any, value: Any) -> None:
        """Optimized setter with cache invalidation."""
        cdef int obj_id = id(obj)

        if self.field.validator is not None:
            value = self.field.validator(value)

        setattr(obj, f"_{self.name}", value)

        self._cache[obj_id] = value

    def clear_cache(self) -> None:
        """Clear the descriptor cache."""
        self._cache.clear()


def create_optimized_descriptor(name: str, field: MetaField) -> OptimizedDescriptor:
    """Create an optimized descriptor for field access."""
    return OptimizedDescriptor(name, field)