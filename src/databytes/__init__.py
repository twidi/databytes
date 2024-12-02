from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from math import prod
from multiprocessing.shared_memory import SharedMemory
from struct import Struct, pack_into, unpack_from
from struct import error as StructError
from typing import (
    Any,
    ClassVar,
    Generator,
    Iterator,
    NamedTuple,
    Optional,
    TypeAlias,
    TypeVar,
    Union,
    cast,
    get_type_hints,
)

from typing_extensions import _AnnotatedAlias

from .types import Buffer, DBType, Dimensions, Endianness, SubStruct

T = TypeVar("T")
BT = TypeVar("BT", bound="BinaryStruct")

RecursiveArray: TypeAlias = Union[list[T], list["RecursiveArray[T]"]]
BinaryStructOrRecursiveArrayOf: TypeAlias = "BinaryStruct" | RecursiveArray["BinaryStructOrRecursiveArrayOf"]


@dataclass
class FieldInfo:
    """Information about a field in the binary structure"""

    name: str
    offset: int
    nb_bytes: int
    db_type: DBType  # type: ignore[type-arg]
    format: str
    dimensions: Dimensions = ()
    sub: Optional[BinaryStructOrRecursiveArrayOf] = None

    def __post_init__(self) -> None:
        # # we'll use unpack_from and pack_into from a struct instance because format is pre-compiled
        self.raw_structs = {endianness: Struct(f"{endianness}{self.format}") for endianness in Endianness}

    @cached_property
    def is_array(self) -> bool:
        return bool(self.dimensions)

    @cached_property
    def nb_dimensions(self) -> int:
        return len(self.dimensions)

    @cached_property
    def nb_items(self) -> int:
        return prod(self.dimensions) if self.dimensions else 1

    def read_from_buffer(self, buffer: Buffer, instance_offset: int, endianness: Endianness) -> Any:
        values = self.raw_structs[endianness].unpack_from(buffer, instance_offset + self.offset)  # type: ignore[arg-type]
        if self.db_type.needs_decoding:
            values = tuple(self.db_type.decode(value) for value in values)
        # For arrays, convert to a list of values and reshape according to dimensions
        return _reshape_array(list(values), self.dimensions) if self.is_array else values[0]

    def write_to_buffer(self, buffer: Buffer, instance_offset: int, endianness: Endianness, value: Any) -> None:
        """Write a value to the buffer at the field's offset.

        Args:
            buffer: The buffer to write to
            value: The value to write
        """
        if isinstance(buffer, bytes):
            raise TypeError("Cannot write to immutable buffer")

        if isinstance(self.db_type, SubStruct):
            # For sub-structs, we don't write directly, it's directly handled by the sub-struct
            return

        values: Iterator[Any]

        # Convert value to the format expected by struct.pack
        if self.is_array:
            # Flatten the array if needed
            if self.nb_dimensions > 1:
                value = _iterate_array_items(value, self.nb_dimensions)

            values = (self.db_type.encode(v) for v in value)
        else:
            # Single value
            values = iter((self.db_type.encode(value),))

        # Pack values into buffer
        try:
            self.raw_structs[endianness].pack_into(buffer, instance_offset + self.offset, *values)  # type: ignore[arg-type]
        except StructError as e:
            raise ValueError(f"Failed to pack value(s) {values} into buffer") from e


def _iterate_array_items(arr: T | RecursiveArray[T], nb_dimensions: int) -> Iterator[T]:
    if nb_dimensions <= 1:
        if isinstance(arr, list):
            yield from cast(list[T], arr)
        else:
            yield arr
        return
    if not isinstance(arr, list):
        raise TypeError(f"Expected list, got {type(arr)}")
    for item in arr:
        yield from _iterate_array_items(item, nb_dimensions - 1)


def _reshape_array(array: list[T], dimensions: Dimensions) -> RecursiveArray[T]:
    """Reshape a flat array into nested lists according to the dimensions.
    For example with dimensions (2, 3) and values [1, 2, 3, 4, 5, 6],
    returns [[1, 2], [3, 4], [5, 6]]."""
    if len(dimensions) <= 1:
        return array
    current: RecursiveArray[T] = array[:]
    for dim in dimensions[:-1]:
        chunk_size = len(current) // (len(current) // dim)
        current = [current[i : i + chunk_size] for i in range(0, len(current), chunk_size)]
    return current


def _extract_dimensions(lst: Any) -> Dimensions:
    if not isinstance(lst, list):
        return ()

    shape = [len(lst)]

    if lst and isinstance(lst[0], list):
        sub_shape = _extract_dimensions(lst[0])

        # Verify all sublists have same shape
        for item in lst[1:]:
            if _extract_dimensions(item) != sub_shape:
                raise ValueError("Inconsistent dimensions")

        shape.extend(sub_shape)

    return tuple(shape[::-1])


class FieldDescriptor:
    """Descriptor for lazy loading binary fields"""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name

    def __get__(
        self,
        instance: Optional[BinaryStruct],
        owner: Optional[type[BinaryStruct]] = None,
    ) -> Any:
        if instance is None:
            return self

        return instance._read_field(self.field_name)

    def __set__(self, instance: BinaryStruct, value: Any) -> None:
        """Set the field value by writing to the buffer.

        Args:
            instance: The BinaryStruct instance
            value: The value to write
        """
        if instance is None:
            return  # type: ignore[unreachable]

        instance._write_field(self.field_name, value)


class BinaryStruct:
    """Base class for binary structures"""

    _endianness: Endianness = Endianness.get_default()
    _fields: ClassVar[dict[str, FieldInfo]] = {}
    _nb_bytes: ClassVar[int] = 0
    _struct_format: ClassVar[str] = ""

    def __init__(self, buffer: Buffer, offset: int = 0, endianness: Endianness | None = None) -> None:
        """Initialize with a buffer and its offset from parent buffer"""
        if len(buffer) < self._nb_bytes:
            raise ValueError(f"Buffer too small: got {len(buffer)} bytes, need {self._nb_bytes}")
        self._buffer: Buffer = buffer
        self._offset = offset
        if endianness is not None:
            self._endianness = endianness
        self._create_sub_instances()

    def _attach_buffer(self, buffer: Buffer, delta_offset: int) -> None:
        self._buffer = buffer
        self._offset += delta_offset

        def update_buffers(structs: BinaryStructOrRecursiveArrayOf) -> None:
            if isinstance(structs, list):
                for struct in structs:
                    update_buffers(struct)
            elif isinstance(structs, BinaryStruct):
                structs._attach_buffer(buffer, delta_offset)

        for field in self._fields.values():
            if not isinstance(field.db_type, SubStruct):
                continue

            if isinstance(field.db_type, SubStruct):
                struct = getattr(self, field.name)
                if struct is not None:
                    update_buffers(struct)

    def attach_buffer(self, buffer: Buffer, offset: int | None = None) -> None:
        """Set the buffer for this struct and update all sub-structs."""
        if len(buffer) < self._nb_bytes:
            raise ValueError(f"Buffer too small: got {len(buffer)} bytes, need {self._nb_bytes}")
        delta_offset = offset - self._offset if offset is not None else 0
        self._attach_buffer(buffer, delta_offset)

    def set_new_buffer(self, buffer: Buffer) -> None:
        # kept for backward compatibility
        self.attach_buffer(buffer)

    def get_raw_content(self) -> tuple[Any, ...]:
        return unpack_from(f"{self._endianness}{self._struct_format}", self._buffer, self._offset)  # type: ignore[arg-type]

    def set_raw_content(self, content: tuple[Any, ...]) -> None:
        try:
            pack_into(f"{self._endianness}{self._struct_format}", self._buffer, self._offset, *content)  # type: ignore[arg-type]
        except StructError as e:
            raise ValueError("Failed to fill content into buffer") from e

    def clear_buffer(self) -> None:
        pack_into(f"{self._endianness}{self._nb_bytes}s", self._buffer, self._offset, b"")  # type: ignore[arg-type]

    def fill_from(self: BT, other: BT) -> None:
        if not isinstance(other, self.__class__):
            raise ValueError(f"Cannot fill {self.__class__.__name__} from {other.__class__.__name__}")
        self.set_raw_content(other.get_raw_content())

    def fill_from_dict(self, data: dict[str, Any], *, clear_unset: bool = False) -> None:
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data)}")

        if clear_unset:
            # clear once and for all so no need to pass the `clear_unset` argument to sub structs
            self.clear_buffer()

        def handle_array(recipient: list[Any], dict_items: list[Any], field_is_struct: bool) -> None:
            for index, dict_item in enumerate(dict_items):
                if isinstance(dict_item, list):
                    handle_array(recipient[index], dict_item, field_is_struct)
                else:
                    if field_is_struct:
                        recipient[index].fill_from_dict(dict_item)
                    else:
                        recipient[index] = dict_item

        for field in self._fields.values():
            if field.name not in data:
                continue

            field_is_struct = isinstance(field.db_type, SubStruct)
            value = data[field.name]

            if not field.is_array:
                if field_is_struct:
                    if not isinstance(value, dict):
                        raise TypeError(f"Expected dict for field {field.name}, got {type(value)}")
                    getattr(self, field.name).fill_from_dict(value)
                else:
                    setattr(self, field.name, value)
                continue

            if not isinstance(value, list):
                raise TypeError(f"Expected list for field {field.name}, got {type(value)}")

            if (other_dimensions := _extract_dimensions(value)) != field.dimensions:
                raise ValueError(
                    f"Invalid dimensions for field {field.name}: "
                    f"got {other_dimensions}, expected {field.dimensions}"
                )

            if field_is_struct:
                recipient = getattr(self, field.name)
            else:
                recipient = _reshape_array([None] * field.nb_items, field.dimensions)

            handle_array(recipient, value, field_is_struct)

            if not field_is_struct:
                setattr(self, field.name, recipient)

    def _to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        value: Any

        for field in self._fields.values():
            value = getattr(self, field.name)

            if not field.is_array:
                result[field.name] = value.to_dict() if isinstance(value, BinaryStruct) else value
                continue

            if field.nb_dimensions > 1:
                value = _iterate_array_items(value, field.nb_dimensions)

            result[field.name] = _reshape_array(
                [struct.to_dict() if isinstance(struct, BinaryStruct) else struct for struct in value], field.dimensions
            )

        return result

    def to_dict(self) -> dict[str, Any]:
        return self._to_dict()

    def _create_sub_instances(self) -> None:
        """Create sub-instances for all sub-struct fields."""

        def create_struct(struct_class: type[BT], offset: int) -> BT:
            return struct_class(self._buffer, offset=offset, endianness=self._endianness)

        for field in self._fields.values():
            if not isinstance(field.db_type, SubStruct):
                continue

            if not field.is_array:
                # if not an array, it's a single struct
                struct = create_struct(field.db_type.python_type, self._offset + field.offset)
                setattr(self, field.name, struct)
                continue

            # get list(s) of structs following the dimensions
            items = []
            for index in range(field.nb_items):
                offset = self._offset + field.offset + (index * field.db_type.single_nb_bytes)
                struct = create_struct(field.db_type.python_type, offset)
                items.append(struct)

            setattr(self, field.name, _reshape_array(items, field.dimensions))

    @classmethod
    def __class_getitem__(cls, params: Any) -> _AnnotatedAlias:
        if not isinstance(params, tuple):
            params = (params,)
        for param in params:
            if not isinstance(param, int) or param <= 0:
                raise TypeError(f"{cls.__name__}[*dimensions]: dimensions should be literal positive integers.")
        return _AnnotatedAlias(cls, params)

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()

        # Get type hints from the class
        hints = {
            name: typ
            for name, typ in get_type_hints(cls, include_extras=True).items()
            if not (hasattr(typ, "__origin__") and typ.__origin__ is ClassVar)
        }

        # Calculate field information
        fields: dict[str, FieldInfo] = {}
        current_offset = 0
        dimensions: list[int]
        db_type: DBType  # type: ignore[type-arg]

        for name, type_hint in hints.items():
            base_type = type_hint
            dimensions = []

            if hasattr(type_hint, "__metadata__"):  # Handle Array types
                base_type = type_hint.__origin__
                if not isinstance(base_type, type):
                    continue
                if not issubclass(base_type, DBType) and not issubclass(base_type, BinaryStruct):
                    continue

                for dimension in type_hint.__metadata__:
                    if not isinstance(dimension, int) or dimension <= 0:
                        raise TypeError(
                            f"{base_type.__name__}[*dimensions]: dimensions should be literal positive integers."
                        )
                    dimensions.append(dimension)

            if not isinstance(base_type, type):
                continue
            if issubclass(base_type, BinaryStruct):
                # Handle nested struct fields
                db_type = SubStruct(python_type=base_type, dimensions=tuple(dimensions))
            elif not issubclass(base_type, DBType):
                continue
            else:
                db_type = base_type(dimensions=tuple(dimensions))

            fields[name] = FieldInfo(
                name=name,
                offset=current_offset,
                nb_bytes=db_type.nb_bytes,
                db_type=db_type,
                format=db_type.struct_format,
                dimensions=db_type.dimensions,
            )
            # Create descriptor for the field
            # (we keep normal access for sub structs, instance fields will be created in `create_sub_instances` at __init__ time)
            if not issubclass(base_type, BinaryStruct):
                setattr(cls, name, FieldDescriptor(name))
            current_offset += fields[name].nb_bytes

        cls._fields = fields
        cls._nb_bytes = current_offset
        cls._struct_format = "".join(field.db_type.struct_format for field in cls._fields.values())

    def _read_field(self, field_name: str) -> Any:
        """Read a field from a buffer"""
        if field_name not in (self._fields or {}):
            raise ValueError(f"Unknown field {field_name}")
        return self._fields[field_name].read_from_buffer(self._buffer, self._offset, self._endianness)

    def _write_field(self, field_name: str, value: Any) -> None:
        """Write a field to a buffer"""
        if field_name not in (self._fields or {}):
            raise ValueError(f"Unknown field {field_name}")
        self._fields[field_name].write_to_buffer(self._buffer, self._offset, self._endianness, value)

    def free_buffer(self) -> None:
        self._buffer = None  # type: ignore[assignment]

        def free_structs(structs: BinaryStructOrRecursiveArrayOf) -> None:
            if isinstance(structs, list):
                for struct in structs:
                    free_structs(struct)
            elif isinstance(structs, BinaryStruct):
                structs.free_buffer()

        for field in self._fields.values():
            if isinstance(field.db_type, SubStruct):
                sub = getattr(self, field.name)
                if sub is not None:
                    free_structs(sub)
