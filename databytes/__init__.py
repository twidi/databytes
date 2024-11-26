from __future__ import annotations

from multiprocessing.shared_memory import SharedMemory
from struct import Struct
from typing import Any, ClassVar, NamedTuple, Optional, get_type_hints

from rich.console import Console
from rich.table import Table

from .types import Buffer, DBType, string


class FieldInfo(NamedTuple):
    """Information about a field in the binary structure"""

    name: str
    struct: Struct  # better to use unpack_from from struct instance because format is pre-compiled
    offset: int
    nb_bytes: int
    db_type: DBType
    format: str
    dimensions: tuple[int, ...] = ()

    @property
    def is_array(self) -> bool:
        return bool(self.dimensions)

    @property
    def nb_dimensions(self) -> int:
        return len(self.dimensions)

    @staticmethod
    def _reshape_array(array: list[Any], dimensions: tuple[int, ...]) -> list[Any]:
        """Reshape a flat array into nested lists according to the dimensions.
        For example with dimensions (2, 3) and values [1, 2, 3, 4, 5, 6],
        returns [[1, 2], [3, 4], [5, 6]]."""
        if len(dimensions) <= 1:
            return array
        current = array
        for dim in dimensions[:-1]:
            new = []
            chunk_size = len(current) // (len(current) // dim)
            for i in range(0, len(current), chunk_size):
                new.append(current[i : i + chunk_size])
            current = new
        return current

    def read_from_buffer(self, buffer: Buffer) -> Any:
        values = self.struct.unpack_from(buffer, self.offset)

        if self.is_array:
            # Special case for char arrays: convert to string
            if self.db_type.collapse_first_dimension:
                # First dimension is kept together length, convert each chunk to string
                items = [
                    self.db_type.convert_first_dimension(value) for value in values
                ]
                if self.nb_dimensions == 1:
                    # Single entry
                    return items[0]
                # Array of items, reshape according to remaining dimensions
                return self._reshape_array(items, self.dimensions[1:])

            # For arrays, convert to a list of values and reshape according to dimensions
            return self._reshape_array(list(values), self.dimensions)

        if isinstance(values[0], bytes):
            # Single char
            return values[0].decode()

        # Single value
        return values[0]


class BinaryField:
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
        if not hasattr(instance, "_buffer"):
            raise ValueError("No buffer available")
        if owner is None:
            raise ValueError("No owner class")
        return owner.read_field(instance._buffer, self.field_name)


class BinaryStruct:
    """Base class for binary structures"""

    _fields: ClassVar[dict[str, FieldInfo]] = {}
    _nb_bytes: ClassVar[int] = 0

    def __init__(self, buffer: Buffer) -> None:
        """Initialize with a buffer"""
        self._buffer: Buffer = buffer

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

        for name, type_hint in hints.items():

            if hasattr(type_hint, "__metadata__"):  # Handle Array types
                base_type = type_hint.__origin__
                if not issubclass(base_type, DBType):
                    continue

                dimensions: list[int] = []
                for dimension in type_hint.__metadata__:
                    if not isinstance(dimension, int) or dimension <= 0:
                        raise TypeError(
                            f"{base_type.__name__}[*dimensions]: dimensions should be literal positive integers."
                        )
                    dimensions.append(dimension)

                db_type = base_type(tuple(dimensions))

            else:  # Handle regular types
                if not issubclass(type_hint, DBType):
                    continue
                db_type = type_hint()

            fields[name] = FieldInfo(
                name=name,
                struct=Struct(format := f"<{db_type.struct_format}"),
                offset=current_offset,
                nb_bytes=db_type.nb_bytes,
                db_type=db_type,
                format=format,
                dimensions=db_type.dimensions,
            )
            # Create descriptor for the field
            setattr(cls, name, BinaryField(name))
            current_offset += fields[name].nb_bytes

        cls._fields = fields
        cls._nb_bytes = current_offset

    @classmethod
    def read_field(cls, buffer: Buffer, field_name: str) -> Any:
        """Read a field from a buffer"""
        if not hasattr(cls, "_fields"):
            raise ValueError("No fields defined")
        if field_name not in cls._fields:
            raise ValueError(f"Unknown field {field_name}")

        return cls._fields[field_name].read_from_buffer(buffer)

    @classmethod
    def print_layout(cls) -> None:
        """Get a string representation of the structure layout"""
        table = Table()

        # Add columns
        table.add_column("Field Name", style="cyan")
        table.add_column("Offset", justify="right", style="magenta")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Format", style="yellow")
        table.add_column("Dimensions", justify="right", style="blue")
        table.add_column("Python Type", style="cyan")

        # Add rows
        for name, info in cls._fields.items():
            dimensions = str(info.dimensions) if info.dimensions else "-"
            python_type = info.db_type.python_type.__name__
            if info.dimensions:
                nb_dimensions = len(info.dimensions)
                if info.db_type.collapse_first_dimension:
                    nb_dimensions -= 1
                python_type = (
                    ("list\[" * nb_dimensions) + python_type + ("]" * nb_dimensions)
                )
            table.add_row(
                name,
                str(info.offset),
                str(info.nb_bytes),
                info.format,
                dimensions,
                python_type,
            )

        # Add total size row
        table.add_section()
        table.add_row(
            "Total Size", "-", str(cls._nb_bytes), "-", "-", "-", style="bold"
        )

        # Render to string
        console = Console(record=True)
        console.print(table)
