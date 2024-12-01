from __future__ import annotations

import array
import builtins
import ctypes
import enum
import mmap
import os
import sys
from functools import cached_property
from math import prod
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeAlias, TypeVar, cast, get_args

import numpy as np
from typing_extensions import _AnnotatedAlias

Buffer: TypeAlias = builtins.bytes | bytearray | memoryview | mmap.mmap | array.array | ctypes.Array | np.ndarray  # type: ignore[type-arg]


Dimensions: TypeAlias = tuple[builtins.int, ...]

DBPythonType = TypeVar("DBPythonType")

NULL = b"\0"


class Endianness(builtins.str, enum.Enum):
    NATIVE = "="
    LITTLE = "<"
    BIG = ">"
    NETWORK = "!"

    def __str__(self) -> builtins.str:
        return self.value

    @property
    def byte_order(self) -> Literal[Endianness.LITTLE, Endianness.BIG]:
        if self == Endianness.NATIVE:
            return Endianness.LITTLE if sys.byteorder == "little" else Endianness.BIG
        if self == Endianness.LITTLE:
            return Endianness.LITTLE
        return Endianness.BIG

    @classmethod
    def get_default(cls) -> Endianness:
        try:
            return cls[os.environ.get("DATABYTES_ENDIANNESS", "") or cls.NATIVE.name]
        except KeyError as exc:
            raise ValueError(
                f"Invalid DATABYTES_ENDIANNESS environment variable value: {os.environ['DATABYTES_ENDIANNESS']}"
            ) from exc


class DBType(Generic[DBPythonType]):
    single_nb_bytes: builtins.int
    single_struct_format: builtins.str
    # `python_type` will be auto set by __init_subclass__ reading the type argument DBPythonType (except for SubStruct)
    python_type: type[DBPythonType]
    dimensions: Dimensions = ()
    needs_decoding = False

    def __init__(self, dimensions: Dimensions = ()) -> None:
        self.dimensions = dimensions

    @cached_property
    def nb_items(self) -> builtins.int:
        return prod(self.dimensions) if self.dimensions else 1

    @cached_property
    def struct_format(self) -> builtins.str:
        return self.single_struct_format if self.nb_items == 1 else f"{self.nb_items}{self.single_struct_format}"

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
            if not isinstance(param, builtins.int) or param <= 0:
                raise TypeError(f"{cls.__name__}[*dimensions]: dimensions should be literal positive integers.")
        return _AnnotatedAlias(cls, params)

    def decode(self, data: builtins.bytes) -> DBPythonType:
        return cast(DBPythonType, data)

    def encode(self, value: DBPythonType) -> DBPythonType:
        if not isinstance(value, self.python_type):
            raise TypeError(f"Expected {self.python_type.__name__}, got {type(value).__name__}")
        return value

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # use `get_original_bases` in python 3.12
        generic_bases = [
            base
            for base in cls.__orig_bases__  # type: ignore[attr-defined]
            if hasattr(base, "__origin__")
        ]
        # Get the actual type argument (DBPythonType) from the first generic base
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

    def encode(self, value: builtins.bytes) -> builtins.bytes:
        value = super().encode(value)
        if len(value) != 1:
            raise ValueError(f"Bytes value must be exactly 1 byte long, got {len(value)}")

        return value


class string(DBType[builtins.str]):
    # used for single strings or arrays of strings (decoded from bytes to str)
    single_nb_bytes = 1
    single_struct_format = "s"  # return a string, not an array of chars
    needs_decoding = True

    def __init__(self, dimensions: Dimensions = ()) -> None:
        # If no dimensions provided, assume it's a single char string
        self.max_length = dimensions[0] if dimensions else 1
        super().__init__(dimensions[1:] if dimensions else ())

    @cached_property
    def struct_format(self) -> builtins.str:
        base = self.single_struct_format if self.max_length == 1 else f"{self.max_length}{self.single_struct_format}"
        return base * self.nb_items

    @cached_property
    def nb_bytes(self) -> builtins.int:
        return self.max_length * super().nb_bytes

    def decode(self, data: builtins.bytes) -> builtins.str:
        return data.rstrip(b"\x00").decode()

    def encode(self, value: builtins.str) -> builtins.bytes:  # type: ignore[override]
        value = super().encode(value)
        encoded = value.encode()
        if len(encoded) > self.max_length:
            raise ValueError(f"String is too long ({len(encoded)} bytes), maximum is {self.max_length} bytes")
        # null padding is handled by the struct
        return encoded


if TYPE_CHECKING:
    from . import BinaryStruct

DBSubStructPythonType = TypeVar("DBSubStructPythonType", bound="BinaryStruct")


class SubStruct(DBType[DBSubStructPythonType]):
    def __init__(self, python_type: type[DBSubStructPythonType], dimensions: Dimensions = ()) -> None:
        super().__init__(dimensions)
        self.python_type = python_type
        self.single_nb_bytes = python_type._nb_bytes
        self.single_struct_format = python_type._struct_format

    @cached_property
    def struct_format(self) -> builtins.str:
        return self.single_struct_format * self.nb_items
