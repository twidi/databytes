import builtins
import struct
from functools import cached_property
from math import prod
from typing import (
    Annotated,
    Any,
    Generic,
    NamedTuple,
    TypeAlias,
    TypeVar,
    cast,
    get_args,
)

from typing_extensions import _AnnotatedAlias

Buffer: TypeAlias = bytes | bytearray | memoryview

T = TypeVar("T")


class DBType(Generic[T]):
    single_nb_bytes: builtins.int
    single_struct_format: str
    python_type: type[
        T
    ]  # will be auto set by __init_subclass__ reading the type argument T
    dimensions: tuple[int, ...] = ()
    collapse_first_dimension: bool = False

    def __init__(self, dimensions: tuple[int, ...] = ()) -> None:
        self.dimensions = dimensions

    @cached_property
    def nb_items(self) -> int:
        return prod(self.dimensions) if self.dimensions else 1

    @cached_property
    def struct_format(self) -> str:
        if self.nb_items == 1:
            return self.single_struct_format
        elif self.collapse_first_dimension:
            length, dimensions = self.dimensions[0], self.dimensions[1:]
            if dimensions:
                return f"{length}{self.single_struct_format}" * prod(dimensions)
            return f"{length}{self.single_struct_format}"
        else:
            return f"{self.nb_items}{self.single_struct_format}"

    @cached_property
    def nb_bytes(self) -> builtins.int:
        return self.nb_items * self.single_nb_bytes

    @classmethod
    def __class_getitem__(cls, params: Any) -> _AnnotatedAlias:
        if cls is DBType:
            return super().__class_getitem__(params)  # type: ignore[misc]
        if not isinstance(params, tuple):
            params = (params,)
        for param in params:
            if not isinstance(param, int) or param <= 0:
                raise TypeError(
                    f"{cls.__name__}[*dimensions]: dimensions should be literal positive integers."
                )
        return _AnnotatedAlias(cls, params)

    def convert_first_dimension(self, data: bytes) -> T:
        return cast(T, data)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # use `get_original_bases` in python 3.12
        generic_bases = [
            base for base in cls.__orig_bases__ if hasattr(base, "__origin__")  # type: ignore[attr-defined]
        ]
        # Get the actual type argument (T) from the first generic base
        cls.python_type = get_args(generic_bases[0])[0]


class uint8(DBType[builtins.int]):
    single_nb_bytes = 1
    single_struct_format = "B"


ubyte = uint8


class int8(DBType[builtins.int]):
    single_nb_bytes = 1
    single_struct_format = "b"


byte = int8


class uint16(DBType[builtins.int]):
    single_nb_bytes = 2
    single_struct_format = "H"


ushort = uint16


class int16(DBType[builtins.int]):
    single_nb_bytes = 2
    single_struct_format = "h"


short = int16


class uint32(DBType[builtins.int]):
    single_nb_bytes = 4
    single_struct_format = "I"


class int32(DBType[builtins.int]):
    single_nb_bytes = 4
    single_struct_format = "i"


class uint64(DBType[builtins.int]):
    single_nb_bytes = 8
    single_struct_format = "Q"


class int64(DBType[builtins.int]):
    single_nb_bytes = 8
    single_struct_format = "q"


class float32(DBType[builtins.float]):
    single_nb_bytes = 4
    single_struct_format = "f"


float = float32


class float64(DBType[builtins.float]):
    single_nb_bytes = 8
    single_struct_format = "d"


double = float64


class bool(DBType[builtins.bool]):
    single_nb_bytes = 1
    single_struct_format = "?"


class char(DBType[builtins.bytes]):
    # used for single chars or arrays of chars (returned as byte or array of bytes)
    single_nb_bytes = 1
    single_struct_format = "c"


class string(DBType[builtins.str]):
    # used for single strings or arrays of strings (decoded from bytes to str)
    single_nb_bytes = 1
    single_struct_format = "s"  # return a string, not an array of chars
    collapse_first_dimension = True

    def convert_first_dimension(self, data: bytes) -> str:
        return data.rstrip(b"\x00").decode()
