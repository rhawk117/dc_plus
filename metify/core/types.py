from __future__ import annotations

import typing

from collections.abc import Callable

T = typing.TypeVar('T')

JSONScalars: typing.TypeAlias = (
    str | int | float | bool | None
)

JSONEncodable: typing.TypeAlias = (
    JSONScalars |
    list['JSONEncodable'] |
    dict[str, 'JSONEncodable']
)



AliasGenerator = Callable[[str], str]
ValidatorFn = Callable[[typing.Any], None]
SerializerFn = Callable[[typing.Any], JSONEncodable]
FactoryFn = Callable[[], typing.Any]

JSONEncoderMapping: typing.TypeAlias = dict[
    type[typing.Any],
    SerializerFn
]




