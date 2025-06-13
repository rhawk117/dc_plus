


def Meta(
    *,
    default: typing.Any = _DCPlusField._MISSING,
    default_factory:  FactoryFn | typing.Any = _DCPlusField._MISSING,
    desc: str | None = None,
    alias: str | None = None,
    validator: ValidatorFn | None = None,
    serializer: SerializerFn | None = None,
    init: bool = True,
    repr: bool = True,
    compare: bool = True,
    hash: bool | None = None,
    kw_only: bool = False,
    **extra: typing.Any
) -> _DCPlusField:
    """Create a field for use in data classes with additional metadata."""
    return _DCPlusField(
        default=default,
        default_factory=default_factory,
        desc=desc,
        alias=alias,
        validator=validator,
        serializer=serializer,
        init=init,
        repr=repr,
        compare=compare,
        hash=hash,
        kw_only=kw_only,
        **extra
    )