'''
**dc_plus**
------------

A minimal extension of the `dataclasses` module that provides a more flexible and powerful way to
define data classes in Python similar to how you would using `pydantic`. However, this library is
not as feature-rich and serves as a lightweight modern alternative to `dataclasses` while providing
the same developer experience and convenience of the `dataclasses` module.

The package is built on top of the standard library's `dataclasses` module to avoid any extra dependencies
to ensure the package size remains small and efficient. It provides a set of utilities and enhancements from
the `dataclasses` module while still following the same principles, but in a more declarative and object-oriented
manner.
'''
from .metadata import ModelOptions, Meta
from .base import ModelBase


__all__ = [
    "ModelBase",
    "ModelOptions",
    "Meta"
]