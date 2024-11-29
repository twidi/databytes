from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from multiprocessing.shared_memory import SharedMemory
from struct import Struct
from struct import error as StructError
from typing import (
    Any,
    ClassVar,
    NamedTuple,
    Optional,
    TypeAlias,
    TypeVar,
    Union,
    get_type_hints,
)

from typing_extensions import _AnnotatedAlias

from .types import Buffer, DBType, Dimensions, Endianness, SubStruct, string

T = TypeVar("T")
BT = TypeVar("BT", bound="BinaryStruct")

RecursiveArray: TypeAlias = Union[list[T], list["RecursiveArray[T]"]]
BinaryStructOrRecursiveArrayOf: TypeAlias = "BinaryStruct" | RecursiveArray["BinaryStructOrRecursiveArrayOf"]


@dataclass
class FieldInfo:
    """Information about a field in the binary structure"""

    name: str
    raw_struct: Struct  # better to use unpack_from from struct instance because format is pre-compiled
    offset: int
    nb_bytes: int
    db_type: DBType  # type: ignore[type-arg]
    format: str
    dimensions: Dimensions = ()
    sub: Optional[BinaryStructOrRecursiveArrayOf] = None

    @cached_property
    def is_array(self) -> bool:
        return bool(self.dimensions)

    @cached_property
    def nb_dimensions(self) -> int:
        return len(self.dimensions)

    @cached_property
    def nb_items(self) -> int:
        if not self.dimensions:
            return 1
        result = 1
        for dimension in self.dimensions:
            result *= dimension
        return result

    @staticmethod
    def _reshape_array(array: list[T], dimensions: Dimensions) -> RecursiveArray[T]:
        """Reshape a flat array into nested lists according to the dimensions.
        For example with dimensions (2, 3) and values [1, 2, 3, 4, 5, 6],
        returns [[1, 2], [3, 4], [5, 6]]."""
        if len(dimensions) <= 1:
            return array
        current: RecursiveArray[T] = array
        for dim in dimensions[:-1]:
            chunk_size = len(current) // (len(current) // dim)
            current = [current[i : i + chunk_size] for i in range(0, len(current), chunk_size)]
        return current

    def read_from_buffer(self, buffer: Buffer, instance_offset: int) -> Any:
        values = self.raw_struct.unpack_from(buffer, instance_offset + self.offset)  # type: ignore[arg-type]
        if self.is_array:
            # Special case for char arrays: convert to string
            if self.db_type.collapse_first_dimension:
                # First dimension is kept together length, convert each chunk to a single value
                items = [self.db_type.convert_first_dimension(value) for value in values]
                if self.nb_dimensions == 1:
                    # Single entry
                    return items[0]
                # Array of items, reshape according to remaining dimensions
                return self._reshape_array(items, self.dimensions[1:])

            # For arrays, convert to a list of values and reshape according to dimensions
            return self._reshape_array(list(values), self.dimensions)

        # Single value
        return values[0]

    def write_to_buffer(self, buffer: Buffer, instance_offset: int, value: Any) -> None:
        """Write a value to the buffer at the field's offset.

        Args:
            buffer: The buffer to write to
            value: The value to write
        """
        if isinstance(buffer, (bytes, str)):
            raise TypeError("Cannot write to immutable buffer")

        if isinstance(self.db_type, SubStruct):
            # For sub-structs, we don't write directly, the buffer property setter handles it
            return

        # Convert value to the format expected by struct.pack
        if self.is_array:
            # Flatten the array if needed
            if self.nb_dimensions > 1:

                def flatten(arr: RecursiveArray[Any], expected_dims: int) -> list[Any]:
                    if expected_dims <= 1:
                        return arr if isinstance(arr, list) else [arr]
                    return [item for sublist in arr for item in flatten(sublist, expected_dims - 1)]

                value = flatten(value, self.nb_dimensions)

            if self.db_type.collapse_first_dimension:
                if self.nb_dimensions == 1:
                    value = [value]
            values = [self.db_type.convert_to_bytes(v) for v in value]
        else:
            # Single value
            values = [self.db_type.convert_to_bytes(value)]

        # Pack values into buffer
        try:
            self.raw_struct.pack_into(buffer, instance_offset + self.offset, *values)  # type: ignore[arg-type]
        except StructError as e:
            raise ValueError(f"Failed to pack value(s) {values} into buffer") from e


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

    _endianness: ClassVar[Endianness] = Endianness.get_default()
    _fields: ClassVar[dict[str, FieldInfo]] = {}
    _nb_bytes: ClassVar[int] = 0
    _struct_format: ClassVar[str] = ""

    def __init__(self, buffer: Buffer, offset: int = 0) -> None:
        """Initialize with a buffer and its offset from parent buffer"""
        if len(buffer) < self._nb_bytes:
            raise ValueError(f"Buffer too small: got {len(buffer)} bytes, need {self._nb_bytes}")
        self._buffer: Buffer = buffer
        self._offset = offset
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

    def _create_sub_instances(self) -> None:
        """Create sub-instances for all sub-struct fields."""

        def create_struct(struct_class: type[BT], offset: int) -> BT:
            if struct_class._endianness != self._endianness:
                raise ValueError(
                    f"Sub-struct {struct_class.__name__} must have same endianness as parent: {self._endianness.name}"
                )
            return struct_class(self._buffer, offset=offset)

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

            setattr(self, field.name, field._reshape_array(items, field.dimensions))

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
                if base_type._endianness != cls._endianness:
                    raise ValueError(
                        f"Sub-struct {base_type.__name__} must have same endianness as parent: {cls._endianness.name}"
                    )

                db_type = SubStruct(python_type=base_type, dimensions=tuple(dimensions))
            elif not issubclass(base_type, DBType):
                continue
            else:
                db_type = base_type(dimensions=tuple(dimensions))

            fields[name] = FieldInfo(
                name=name,
                raw_struct=Struct(format := f"{cls._endianness}{db_type.struct_format}"),
                offset=current_offset,
                nb_bytes=db_type.nb_bytes,
                db_type=db_type,
                format=format if db_type.struct_format else "struct",
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
        return self._fields[field_name].read_from_buffer(self._buffer, self._offset)

    def _write_field(self, field_name: str, value: Any) -> None:
        """Write a field to a buffer"""
        if field_name not in (self._fields or {}):
            raise ValueError(f"Unknown field {field_name}")
        self._fields[field_name].write_to_buffer(self._buffer, self._offset, value)

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
