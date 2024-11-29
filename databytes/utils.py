from __future__ import annotations

from math import prod
from typing import NamedTuple, TypeAlias, Union

from . import BinaryStruct
from .types import Dimensions, SubStruct


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
    elif isinstance(struct_or_class, type) and issubclass(
        struct_or_class, BinaryStruct
    ):
        base_offset = 0
        struct_class = struct_or_class
    else:
        raise ValueError(
            "Expected BinaryStruct or type[BinaryStruct], got {}".format(
                type(struct_or_class)
            )
        )

    fields: FieldsLayoutInfo = {}
    python_type: type
    for name, field in struct_or_class._fields.items():
        python_type = field.db_type.python_type
        dimensions = field.dimensions if field.dimensions else None
        nb_items = 1
        if dimensions is not None:
            if field.db_type.collapse_first_dimension:
                dimensions = dimensions[1:]
            if dimensions:
                for _ in dimensions:
                    python_type = list[python_type]  # type: ignore[valid-type]
                nb_items = prod(dimensions)
            else:
                dimensions = None

        is_sub_struct = isinstance(field.db_type, SubStruct)
        sub_struct_info: StructLayoutInfo | None = None
        if is_sub_struct and include_sub_structs_details:
            sub_struct_info = get_layout_info(field.db_type.python_type, True)

        fields[name] = FieldLayoutInfo(
            name=name,
            offset=base_offset + field.offset,
            nb_bytes=field.nb_bytes,
            struct_format=field.db_type.struct_format,
            nb_items=nb_items,
            dimensions=dimensions,
            python_type=field.db_type.python_type,
            python_full_type=python_type,
            is_sub_struct=is_sub_struct,
            sub_struct=sub_struct_info,
        )

    return StructLayoutInfo(
        struct_class=struct_class,
        name=struct_class.__name__,
        struct_format=struct_or_class._struct_format,
        nb_bytes=struct_or_class._nb_bytes,
        offset=base_offset,
        fields=fields,
    )
