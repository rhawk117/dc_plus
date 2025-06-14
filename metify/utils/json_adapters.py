"""Dynamic JSON encoder/decoder adapter system for optimal performance."""
from __future__ import annotations

import json
import functools
from typing import Any, Literal, Protocol

__all__ = ['get_json_encoder', 'get_json_decoder', 'register_json_adapter']


class JSONEncoder(Protocol):
    """Protocol for JSON encoding functions."""
    def __call__(self, obj: Any, **kwargs: Any) -> str: ...


class JSONDecoder(Protocol):
    """Protocol for JSON decoding functions."""
    def __call__(self, data: str | bytes | bytearray, **kwargs: Any) -> Any: ...


# Global Registry of available JSON adapters
_ENCODERS: dict[str, JSONEncoder] = {}
_DECODERS: dict[str, JSONDecoder] = {}


def _init_standard_json() -> None:
    """Initialize standard library JSON adapter."""
    _ENCODERS['json'] = json.dumps


    _DECODERS['json'] = json.loads # type: ignore[assignment]


def _init_orjson() -> None:
    """Initialize orjson adapter with optimal settings."""
    try:
        import orjson # type: ignore[import]

        def orjson_encoder(obj: Any, **kwargs: Any) -> str:
            options = 0
            if kwargs.get('indent'):
                options |= orjson.OPT_INDENT_2
            if kwargs.get('sort_keys'):
                options |= orjson.OPT_SORT_KEYS

            default = kwargs.get('default')
            return orjson.dumps(obj, default=default, option=options).decode('utf-8')

        def orjson_decoder(data: str, **kwargs: Any) -> Any:
            return orjson.loads(data)

        _ENCODERS['orjson'] = orjson_encoder
        _DECODERS['orjson'] = orjson_decoder # type: ignore[assignment]
    except ImportError:
        pass


def _init_ujson() -> None:
    """Initialize ujson adapter."""
    try:
        import ujson # type: ignore[import]

        def ujson_encoder(obj: Any, **kwargs: Any) -> str:
            return ujson.dumps(
                obj,
                indent=kwargs.get('indent', 0),
                sort_keys=kwargs.get('sort_keys', False),
                ensure_ascii=kwargs.get('ensure_ascii', True),
                default=kwargs.get('default')
            )

        _ENCODERS['ujson'] = ujson_encoder
        _DECODERS['ujson'] = ujson.loads # type: ignore[assignment]
    except ImportError:
        pass


def _init_msgspec() -> None:
    '''Attempts to initialize the msgspec JSON adapter by importing the msgspec library.'''
    try:
        import msgspec # type: ignore[import]

        _msgspec_encoder = msgspec.json.Encoder()
        _msgspec_decoder = msgspec.json.Decoder()

        def msgspec_encoder(obj: Any, **kwargs: Any) -> str:
            return _msgspec_encoder.encode(obj).decode('utf-8')

        def msgspec_decoder(data: str, **kwargs: Any) -> Any:
            return _msgspec_decoder.decode(data.encode('utf-8'))

        _ENCODERS['msgspec'] = msgspec_encoder
        _DECODERS['msgspec'] = msgspec_decoder # type: ignore[assignment]

    except ImportError:
        pass


def _init_rapidjson() -> None:
    '''Attempts to initialize the rapidjson JSON adapter by importing the rapidjson library.'''
    try:
        import rapidjson # type: ignore[import]

        def rapidjson_encoder(obj: Any, **kwargs: Any) -> str:
            return rapidjson.dumps(
                obj,
                indent=kwargs.get('indent'),
                sort_keys=kwargs.get('sort_keys', False),
                ensure_ascii=kwargs.get('ensure_ascii', True),
                default=kwargs.get('default')
            )

        _ENCODERS['rapidjson'] = rapidjson_encoder
        _DECODERS['rapidjson'] = rapidjson.loads

    except ImportError:
        pass


_init_standard_json()
_init_orjson()
_init_ujson()
_init_msgspec()
_init_rapidjson()

SupportedEncoders = Literal[
    'json', 'orjson', 'ujson', 'msgspec', 'rapidjson'
]

@functools.lru_cache(maxsize=16)
def get_json_encoder(name: SupportedEncoders) -> JSONEncoder:
    """Gets a supported JSON encoder by name with fallback to
    standard json.

    Parameters
    ----------
    name : str
        Name of the encoder ('json', 'orjson', 'ujson', 'msgspec', 'rapidjson')

    Returns
    -------
    JSONEncoder
        Encoder function that converts objects to JSON strings

    Notes
    -----
    The function attempts to load the requested encoder. If the encoder
    is not available (not installed), it falls back to the standard
    library json module and issues a warning.
    """
    if name in _ENCODERS:
        return _ENCODERS[name]

    if name not in {'json', 'orjson', 'ujson', 'msgspec', 'rapidjson'}:
        raise ValueError(f"Unknown JSON encoder: {name}")

    import warnings
    warnings.warn(
        f"JSON encoder '{name}' not available, falling back to standard json. "
        f"Install {name} for better performance.",
        RuntimeWarning,
        stacklevel=2
    )
    return _ENCODERS['json']


@functools.lru_cache(maxsize=16)
def get_json_decoder(name: SupportedEncoders) -> JSONDecoder:
    """Get JSON decoder by name with fallback to standard json.

    Parameters
    ----------
    name : str
        Name of the decoder ('json', 'orjson', 'ujson', 'msgspec', 'rapidjson')

    Returns
    -------
    JSONDecoder
        Decoder function that parses JSON strings to objects
    """
    if name in _DECODERS:
        return _DECODERS[name]

    import warnings
    warnings.warn(
        f"JSON decoder '{name}' not available, falling back to standard json. "
        f"Install {name} for better performance.",
        RuntimeWarning,
        stacklevel=2
    )
    return _DECODERS['json']


def register_json_adapter(
    name: str,
    encoder: JSONEncoder,
    decoder: JSONDecoder
) -> None:
    """Register a custom JSON encoder/decoder pair.

    Parameters
    ----------
    name : str
        Name for the adapter
    encoder : JSONEncoder
        Function that encodes objects to JSON strings
    decoder : JSONDecoder
        Function that decodes JSON strings to objects

    Examples
    --------
    >>> def custom_encoder(obj, **kwargs):
    ...     return json.dumps(obj, cls=MyCustomEncoder, **kwargs)
    >>>
    >>> register_json_adapter('custom', custom_encoder, json.loads)
    """
    _ENCODERS[name] = encoder
    _DECODERS[name] = decoder
    get_json_encoder.cache_clear()
    get_json_decoder.cache_clear()


def benchmark_json_adapters(*, data: Any, iterations: int = 1000) -> dict[str, dict[str, float]]:
    """Benchmark available JSON adapters for performance comparison.

    Parameters
    ----------
    data : Any
        Sample data to benchmark with
    iterations : int, default=1000
        Number of iterations for timing

    Returns
    -------
    dict[str, dict[str, float]]
        Timing results for each adapter's encode and decode operations
    """
    import time

    results = {}
    encoded_data = json.dumps(data)

    for name in _ENCODERS:
        encoder = _ENCODERS[name]
        decoder = _DECODERS.get(name)

        if not decoder:
            continue

        start = time.perf_counter()
        for _ in range(iterations):
            encoder(data)

        encode_time = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(iterations):
            decoder(encoded_data)

        decode_time = time.perf_counter() - start

        # in ms per operation
        results[name] = {
            'encode': encode_time / iterations * 1000,
            'decode': decode_time / iterations * 1000
        }

    return results