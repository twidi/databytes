from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NamedTuple, TypeAlias, Union

from . import BinaryStruct
from .types import Dimensions, Endianness, SubStruct

if TYPE_CHECKING:
    from rich.group import Group, Table  # type: ignore[import-not-found]


class FieldLayoutInfo(NamedTuple):
    name: str
    offset: int
    nb_bytes: int
    struct_format: str
    nb_items: int
    dimensions: Dimensions | None
    python_type: type
    python_full_type: type
    is_sub_struct: bool
    sub_struct: StructLayoutInfo | None = None


FieldsLayoutInfo: TypeAlias = dict[str, FieldLayoutInfo]


class StructLayoutInfo(NamedTuple):
    name: str
    struct_class: type
    endianness: Endianness
    byte_order: Literal[Endianness.LITTLE, Endianness.BIG]
    struct_format: str
    nb_bytes: int
    offset: int
    fields: FieldsLayoutInfo


def get_layout_info(
    struct_or_class: Union[BinaryStruct, type[BinaryStruct]],
    include_sub_structs_details: bool = False,
) -> StructLayoutInfo:
    """Get a representation of the structure layout."""
    if isinstance(struct_or_class, BinaryStruct):
        base_offset = struct_or_class._offset
        struct_class = struct_or_class.__class__
    elif isinstance(struct_or_class, type) and issubclass(struct_or_class, BinaryStruct):
        base_offset = 0
        struct_class = struct_or_class
    else:
        raise ValueError("Expected BinaryStruct or type[BinaryStruct], got {}".format(type(struct_or_class)))

    fields: FieldsLayoutInfo = {}
    python_type: type
    for name, field in struct_or_class._fields.items():
        python_type = field.db_type.python_type
        if field.dimensions is not None:
            for _ in field.dimensions:
                python_type = list[python_type]  # type: ignore[valid-type]

        is_sub_struct = isinstance(field.db_type, SubStruct)
        sub_struct_info: StructLayoutInfo | None = None
        if is_sub_struct and include_sub_structs_details:
            sub_struct_info = get_layout_info(field.db_type.python_type, True)

        fields[name] = FieldLayoutInfo(
            name=name,
            offset=base_offset + field.offset,
            nb_bytes=field.nb_bytes,
            struct_format=field.db_type.struct_format,
            nb_items=field.nb_items,
            dimensions=field.dimensions or None,
            python_type=field.db_type.python_type,
            python_full_type=python_type,
            is_sub_struct=is_sub_struct,
            sub_struct=sub_struct_info,
        )

    return StructLayoutInfo(
        name=struct_class.__name__,
        struct_class=struct_class,
        endianness=struct_or_class._endianness,
        byte_order=struct_or_class._endianness.byte_order,
        struct_format=struct_or_class._struct_format,
        nb_bytes=struct_or_class._nb_bytes,
        offset=base_offset,
        fields=fields,
    )


def _get_rich_tables(
    struct_or_class: Union[BinaryStruct, type[BinaryStruct]],
    include_sub_structs_details: bool = False,
) -> dict[type[BinaryStruct], "Table"]:
    """Get a string representation, as a table, of the structure layout"""

    try:
        from rich.table import Table
    except ImportError as exc:
        raise ImportError("`rich` library is not installed") from exc

    layout = get_layout_info(struct_or_class, include_sub_structs_details)

    table = Table(title=f"Layout of {layout.name} ({layout.nb_bytes} bytes)")

    # Add columns
    table.add_column("Name", style="cyan")
    table.add_column("Offset", justify="right", style="magenta")
    table.add_column("Nb bytes", justify="right", style="green")
    table.add_column("Format", style="yellow")
    table.add_column("Dimensions", justify="right", style="blue")
    table.add_column("Python Type", style="cyan")

    # Add rows
    for field in layout.fields.values():
        python_type = str(field.python_full_type).replace("<class '", "").replace("'>", "")
        if "." in python_type:
            start, *_, end = python_type.split(".")
            python_type = (start.rsplit("[", 1)[0] + "[" + end) if "[" in start else end

        table.add_row(
            field.name,
            str(field.offset),
            str(field.nb_bytes),
            field.struct_format,
            str(field.dimensions),
            python_type.replace("[", r"\["),
        )

    tables: dict[type[BinaryStruct], Table] = {layout.struct_class: table}

    if include_sub_structs_details:
        for field in layout.fields.values():
            if field.is_sub_struct and field.python_type not in tables:
                tables[field.python_type] = get_rich_table(field.python_type, True)

    return tables


def get_rich_table(
    struct_or_class: Union[BinaryStruct, type[BinaryStruct]],
    include_sub_structs_details: bool = False,
) -> "Group":
    tables = _get_rich_tables(struct_or_class, include_sub_structs_details)
    from rich.console import Group

    return Group(*tables.values())


def get_rich_table_string(
    struct_or_class: Union[BinaryStruct, type[BinaryStruct]],
    include_sub_structs_details: bool = False,
) -> str:
    table = get_rich_table(struct_or_class, include_sub_structs_details)

    from rich.console import Console

    table.title = None

    console = Console(record=True)
    with console.capture() as capture:
        console.print(table)

    return capture.get()


def print_rich_table(
    struct_or_class: Union[BinaryStruct, type[BinaryStruct]],
    include_sub_structs_details: bool = False,
) -> None:
    print(get_rich_table_string(struct_or_class, include_sub_structs_details))
