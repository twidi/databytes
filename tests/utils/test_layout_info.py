from databytes import BinaryStruct
from databytes import types as t
from databytes.utils import Endianness, FieldLayoutInfo, StructLayoutInfo, get_layout_info


class SimpleSubStruct(BinaryStruct):
    """A simple sub-struct with two basic fields."""

    field1: t.uint8
    field2: t.uint16


class ComplexStruct(BinaryStruct):
    """A test struct with various field types and dimensions."""

    # Field with no dimension
    simple_int: t.uint32
    # String with one dimension, the max lengths
    fixed_string: t.string[10]
    # Matrix of fixed-length strings
    string_matrix: t.string[4, 3, 2]  # list of 2 lists of 3 strings of max length 4
    # Field as an array
    int_array: t.uint16[3]
    # Field as a matrix
    float_matrix: t.float32[2, 3]
    # Single sub-struct
    sub: SimpleSubStruct
    # Array of sub-struct
    sub_array: SimpleSubStruct[2]
    # Matrix of sub-struct
    sub_matrix: SimpleSubStruct[2, 3]


def get_expected_simple_sub_struct_layout_info(
    base_offset: int = 0,
) -> StructLayoutInfo:
    return StructLayoutInfo(
        name="SimpleSubStruct",
        struct_class=SimpleSubStruct,
        endianness=Endianness.LITTLE,
        byte_order=Endianness.LITTLE,
        struct_format="BH",
        nb_bytes=3,
        offset=base_offset,
        fields={
            "field1": FieldLayoutInfo(
                name="field1",
                offset=base_offset,
                nb_bytes=1,
                struct_format="B",
                nb_items=1,
                dimensions=None,
                python_type=int,
                python_full_type=int,
                is_sub_struct=False,
            ),
            "field2": FieldLayoutInfo(
                name="field2",
                offset=base_offset + 1,
                nb_bytes=2,
                struct_format="H",
                nb_items=1,
                dimensions=None,
                python_type=int,
                python_full_type=int,
                is_sub_struct=False,
            ),
        },
    )


def get_expected_complex_struct_layout_info(base_offset: int = 0, with_subs: bool = False) -> StructLayoutInfo:
    return StructLayoutInfo(
        name="ComplexStruct",
        struct_class=ComplexStruct,
        endianness=Endianness.LITTLE,
        byte_order=Endianness.LITTLE,
        struct_format="I10s4s4s4s4s4s4s3H6fBHBHBHBHBHBHBHBHBH",
        nb_bytes=95,
        offset=base_offset,
        fields={
            "simple_int": FieldLayoutInfo(
                name="simple_int",
                offset=base_offset,
                nb_bytes=4,
                struct_format="I",
                nb_items=1,
                dimensions=None,
                python_type=int,
                python_full_type=int,
                is_sub_struct=False,
            ),
            "fixed_string": FieldLayoutInfo(
                name="fixed_string",
                offset=base_offset + 4,
                nb_bytes=10,
                struct_format="10s",
                nb_items=1,
                dimensions=None,
                python_type=str,
                python_full_type=str,
                is_sub_struct=False,
            ),
            "string_matrix": FieldLayoutInfo(
                name="string_matrix",
                offset=base_offset + 14,
                nb_bytes=24,
                struct_format="4s4s4s4s4s4s",
                nb_items=6,
                dimensions=(3, 2),
                python_type=str,
                python_full_type=list[list[str]],
                is_sub_struct=False,
            ),
            "int_array": FieldLayoutInfo(
                name="int_array",
                offset=base_offset + 38,
                nb_bytes=6,
                struct_format="3H",
                nb_items=3,
                dimensions=(3,),
                python_type=int,
                python_full_type=list[int],
                is_sub_struct=False,
            ),
            "float_matrix": FieldLayoutInfo(
                name="float_matrix",
                offset=base_offset + 44,
                nb_bytes=24,
                struct_format="6f",
                nb_items=6,
                dimensions=(2, 3),
                python_type=float,
                python_full_type=list[list[float]],
                is_sub_struct=False,
            ),
            "sub": FieldLayoutInfo(
                name="sub",
                offset=base_offset + 68,
                nb_bytes=3,
                struct_format="BH",
                nb_items=1,
                dimensions=None,
                python_type=SimpleSubStruct,
                python_full_type=SimpleSubStruct,
                is_sub_struct=True,
                sub_struct=(get_expected_simple_sub_struct_layout_info() if with_subs else None),
            ),
            "sub_array": FieldLayoutInfo(
                name="sub_array",
                offset=base_offset + 71,
                nb_bytes=6,
                struct_format="BHBH",
                nb_items=2,
                dimensions=(2,),
                python_type=SimpleSubStruct,
                python_full_type=list[SimpleSubStruct],
                is_sub_struct=True,
                sub_struct=(get_expected_simple_sub_struct_layout_info() if with_subs else None),
            ),
            "sub_matrix": FieldLayoutInfo(
                name="sub_matrix",
                offset=base_offset + 77,
                nb_bytes=18,
                struct_format="BHBHBHBHBHBH",
                nb_items=6,
                dimensions=(2, 3),
                python_type=SimpleSubStruct,
                python_full_type=list[list[SimpleSubStruct]],
                is_sub_struct=True,
                sub_struct=(get_expected_simple_sub_struct_layout_info() if with_subs else None),
            ),
        },
    )


def test_get_layout_info_for_class() -> None:
    """Test the get_layout_info function with a complex struct."""
    assert get_layout_info(ComplexStruct) == get_expected_complex_struct_layout_info()
    assert get_layout_info(ComplexStruct, True) == get_expected_complex_struct_layout_info(with_subs=True)


def test_get_layout_info_for_instance() -> None:
    """Test get_layout_info with a struct instance."""
    buffer = bytearray(ComplexStruct._nb_bytes + 10)
    instance = ComplexStruct(buffer, offset=10)

    assert get_layout_info(instance) == get_expected_complex_struct_layout_info(base_offset=10)
    assert get_layout_info(instance, True) == get_expected_complex_struct_layout_info(base_offset=10, with_subs=True)
