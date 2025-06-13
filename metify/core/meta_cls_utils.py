
from __future__ import annotations


from collections.abc import Generator, Mapping
import typing
from ..config import ModelConfig
from . import const


if typing.TYPE_CHECKING:
    from .field_cls import MetifyField


class _ModelDefiniton:
    __slots__ = ('fields', 'alias_map', 'extras')

    def __init__(self) -> None:
        self.fields: dict[str, MetifyField] = {}
        self.alias_map: dict[str, str] = {}
        self.extras: dict[str, typing.Any] = {}


def is_metify_field(value: typing.Any) -> bool:
    return isinstance(value, MetifyField)

def split_field_annotation(annotation: typing.Any) -> tuple[typing.Any, list[MetifyField]]:
    if not typing.get_origin(annotation) is typing.Annotated:
        return annotation, []
    base_type, *metadata = typing.get_args(annotation)
    field_defs = [meta for meta in metadata if isinstance(meta, MetifyField)]
    return base_type, field_defs


def resolve_model_namespace(namespace: dict[str, typing.Any]) -> _ModelDefiniton:
    definition = _ModelDefiniton()
    annotations = dict(namespace.get('__annotations__', {}))

    for attribute, annotation in annotations.items():
        base_type, fields = split_field_annotation(annotation)

        if is_metify_field(base_type):
            inferred_field = namespace.pop(attribute)
            fields.append(inferred_field)

        elif fields:
            inferred_field = fields[-1]

        else:
            inferred_field = MetifyField()

        inferred_default = namespace.get(attribute)
        if inferred_default and not is_metify_field(inferred_default):
            inferred_field.default = namespace.pop(attribute)

        inferred_field.name = attribute
        inferred_field.type = base_type
        fields.append(inferred_field)

        if inferred_field.alias:
            definition.alias_map[inferred_field.alias] = attribute

        if inferred_field.extra:
            definition.extras[attribute] = inferred_field.extra

        annotation[attribute] = base_type

    namespace['__annotations__'] = annotations
    return definition

def resolve_model_config(
    bases: tuple[type, ...],
    namespace: dict[str, typing.Any],
    fields: tuple[MetifyField, ...]
) -> dict:
    config_dict = {}
    for base in reversed(bases):
        if not isinstance(base, ModelMetadata):
            continue
        parent_config = getattr(base, '__mtf_config__', {})
        config_dict.update(parent_config)

    config_dict.update(
        namespace.pop('model_config', {})
    )

    if 'slots' in config_dict:
        namespace['__slots__'] = tuple(
            field.name for field in fields
        )

    return config_dict



class ModelMetadata:
    __mtf_fields__: tuple[MetifyField, ...]
    __mtf_alias_map__: dict[str, str]
    __mtf_extras__: dict[str, typing.Any]
    __mtf_config__: ModelConfig

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        ns: dict[str, typing.Any],
        **kw
    ) -> typing.Any:
        model_definition = resolve_model_namespace(ns)
        model_config = resolve_model_config(bases, ns, model_definition.fields)