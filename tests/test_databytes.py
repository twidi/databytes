import struct
import sys
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path
from typing import Any

import pytest

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from databytes import BinaryStruct
from databytes import types as t


class MySubSubStruct(BinaryStruct):
    simple: t.uint8


class MySubStruct(BinaryStruct):
    foo: t.string[5]  # a string of 5 chars max
    bar: t.uint16
    qux: t.string[5, 2]  # a list of 2 strings of 5 chars max
    sub: MySubSubStruct  # a sub-struct
    subs: MySubSubStruct[2, 2]  # a 2x2 list of sub-structs


class MyStruct(BinaryStruct):
    uint16: t.uint16
    char: t.char  # a single char
    strings: t.string[10, 2]  # a list of 2 strings of 10 chars max
    chars: t.char[5, 2]  # a list of 2 lists of 5 chars
    float64: t.double
    uint16s: t.uint16[3, 2, 2]  # a list of 2 lists of 2 lists of 3 uint16
    child: MySubStruct  # a sub-struct
    children: MySubStruct[2]  # a list of 2 sub-structs


@pytest.fixture
def test_data() -> bytes:
    """Create sample test data for the tests."""
    return (
        struct.pack("<H", 12345)  # uint16
        + b"X"  # char
        + b"Hello\x00\x00\x00\x00\x00"  # string[10]
        + b"World\x00\x00\x00\x00\x00"  # string[10]
        + b"Hello"  # chars[5]
        + b"World"  # chars[5]
        + struct.pack("<d", 3.14159)  # float64
        + struct.pack("<3H", 1, 2, 3)  # uint16s[3], element 0
        + struct.pack("<3H", 4, 5, 6)  # uint16s[3], element 1
        + struct.pack("<3H", 7, 8, 9)  # uint16s[3], element 2
        + struct.pack("<3H", 10, 11, 12)  # uint16s[3], element 3
        # child: MySubStruct
        + b"Child"  # foo: string[5]
        + struct.pack("<H", 42)  # bar: uint16
        + b"qux00"  # qux[0]: string[5]
        + b"qux01"  # qux[1]: string[5]
        + struct.pack("<B", 1)  # sub.simple: MySubSubStruct
        + struct.pack("<B", 2)  # subs[0][0].simple: MySubSubStruct
        + struct.pack("<B", 3)  # subs[0][1].simple: MySubSubStruct
        + struct.pack("<B", 4)  # subs[1][0].simple: MySubSubStruct
        + struct.pack("<B", 5)  # subs[1][1].simple: MySubSubStruct
        # children: MySubStruct * 2
        # children[0]: MySubStruct
        + b"Kid 1"  # children[0].foo: string[5]
        + struct.pack("<H", 101)  # children[0].bar: uint16
        + b"qux10"  # children[0].qux[0]: string[5]
        + b"qux11"  # children[0].qux[1]: string[5]
        + struct.pack("<B", 6)  # children[0].sub.simple: MySubSubStruct
        + struct.pack("<B", 7)  # children[0].subs[0][0].simple: MySubSubStruct
        + struct.pack("<B", 8)  # children[0].subs[0][1].simple: MySubSubStruct
        + struct.pack("<B", 9)  # children[0].subs[1][0].simple: MySubSubStruct
        + struct.pack("<B", 10)  # children[0].subs[1][1].simple: MySubSubStruct
        # children[1]: MySubStruct
        + b"Kid 2"  # children[1].foo: string[5]
        + struct.pack("<H", 102)  # children[1].bar: uint16
        + b"qux20"  # children[1].qux[0]: string[5]
        + b"qux21"  # children[1].qux[1]: string[5]
        + struct.pack("<B", 11)  # children[1].sub.simple: MySubSubStruct
        + struct.pack("<B", 12)  # children[1].subs[0][0].simple: MySubSubStruct
        + struct.pack("<B", 13)  # children[1].subs[0][1].simple: MySubSubStruct
        + struct.pack("<B", 14)  # children[1].subs[1][0].simple: MySubSubStruct
        + struct.pack("<B", 15)  # children[1].subs[1][1].simple: MySubSubStruct
    )


def verify_struct_values(data: MyStruct) -> None:
    """Helper to verify values from a struct instance."""
    # Test main struct values
    assert data.uint16 == 12345
    assert data.char == b"X"
    assert data.strings == ["Hello", "World"]
    assert data.chars == [
        [b"H", b"e", b"l", b"l", b"o"],
        [b"W", b"o", b"r", b"l", b"d"],
    ]
    assert abs(data.float64 - 3.14159) < 1e-6
    assert data.uint16s == [
        [[1, 2, 3], [4, 5, 6]],
        [[7, 8, 9], [10, 11, 12]],
    ]

    # Test child struct
    assert data.child.foo == "Child"
    assert data.child.bar == 42
    assert data.child.qux == ["qux00", "qux01"]
    assert data.child.sub.simple == 1
    assert data.child.subs[0][0].simple == 2
    assert data.child.subs[0][1].simple == 3
    assert data.child.subs[1][0].simple == 4
    assert data.child.subs[1][1].simple == 5

    # Test children array
    assert data.children[0].foo == "Kid 1"
    assert data.children[0].bar == 101
    assert data.children[0].qux == ["qux10", "qux11"]
    assert data.children[0].sub.simple == 6
    assert data.children[0].subs[0][0].simple == 7
    assert data.children[0].subs[0][1].simple == 8
    assert data.children[0].subs[1][0].simple == 9
    assert data.children[0].subs[1][1].simple == 10

    assert data.children[1].foo == "Kid 2"
    assert data.children[1].bar == 102
    assert data.children[1].qux == ["qux20", "qux21"]
    assert data.children[1].sub.simple == 11
    assert data.children[1].subs[0][0].simple == 12
    assert data.children[1].subs[0][1].simple == 13
    assert data.children[1].subs[1][0].simple == 14
    assert data.children[1].subs[1][1].simple == 15


def get_struct_layout(struct_class: type[BinaryStruct]) -> dict[str, dict[str, Any]]:
    """Get a dictionary representation of the structure layout."""
    layout = {}
    for name, field in struct_class._fields.items():
        dimensions = field.dimensions if field.dimensions else None
        python_type = field.db_type.python_type.__name__
        if field.dimensions:
            nb_dimensions = len(field.dimensions)
            if field.db_type.collapse_first_dimension:
                nb_dimensions -= 1
            python_type = (
                ("list[" * nb_dimensions) + python_type + ("]" * nb_dimensions)
            )
        layout[name] = {
            "offset": field.offset,
            "size": field.nb_bytes,
            "format": field.db_type.struct_format,
            "dimensions": dimensions,
            "python_type": python_type,
        }
    return layout


def test_shared_memory(test_data: bytes) -> None:
    """Test using shared memory buffer."""
    shm = SharedMemory(create=True, size=MyStruct._nb_bytes)
    data: MyStruct | None = None
    try:
        shm.buf[:] = test_data
        data = MyStruct(shm.buf)
        verify_struct_values(data)
    finally:
        if data is not None:
            data.free_buffer()
        shm.close()
        shm.unlink()


def test_bytearray(test_data: bytes) -> None:
    """Test using bytearray buffer."""
    buffer = bytearray(test_data)
    data = MyStruct(buffer)
    verify_struct_values(data)


def test_bytes(test_data: bytes) -> None:
    """Test using bytes buffer."""
    data = MyStruct(test_data)
    verify_struct_values(data)


def test_struct_layout() -> None:
    """Test the structure layout sizes and offsets."""
    # MySubSubStruct layout
    assert MySubSubStruct._nb_bytes == 1
    assert MySubSubStruct._struct_format == "B"
    assert get_struct_layout(MySubSubStruct) == {
        "simple": {
            "offset": 0,
            "size": 1,
            "format": "B",
            "dimensions": None,
            "python_type": "int",
        }
    }

    # MySubStruct layout
    assert MySubStruct._nb_bytes == 22  # 5 + 2 + (5*2) + 1 + (1*2*2)
    assert MySubStruct._struct_format == "5sH5s5sBBBBB"
    assert get_struct_layout(MySubStruct) == {
        "foo": {
            "offset": 0,
            "size": 5,
            "format": "5s",
            "dimensions": (5,),
            "python_type": "str",
        },
        "bar": {
            "offset": 5,
            "size": 2,
            "format": "H",
            "dimensions": None,
            "python_type": "int",
        },
        "qux": {
            "offset": 7,
            "size": 10,
            "format": "5s5s",
            "dimensions": (5, 2),
            "python_type": "list[str]",
        },
        "sub": {
            "offset": 17,
            "size": 1,
            "format": "B",
            "dimensions": None,
            "python_type": "MySubSubStruct",
        },
        "subs": {
            "offset": 18,
            "size": 4,
            "format": "BBBB",
            "dimensions": (2, 2),
            "python_type": "list[list[MySubSubStruct]]",
        },
    }

    # MyStruct layout
    expected_size = (
        2  # uint16
        + 1  # char
        + (10 * 2)  # strings
        + (5 * 2)  # chars
        + 8  # float64
        + (2 * 3 * 2 * 2)  # uint16s
        + 22  # child (MySubStruct)
        + (22 * 2)  # children (MySubStruct[2])
    )
    assert MyStruct._nb_bytes == expected_size
    assert (
        MyStruct._struct_format == "Hc10s10s10cd12H5sH5s5sBBBBB5sH5s5sBBBBB5sH5s5sBBBBB"
    )
    assert get_struct_layout(MyStruct) == {
        "uint16": {
            "offset": 0,
            "size": 2,
            "format": "H",
            "dimensions": None,
            "python_type": "int",
        },
        "char": {
            "offset": 2,
            "size": 1,
            "format": "c",
            "dimensions": None,
            "python_type": "bytes",
        },
        "strings": {
            "offset": 3,
            "size": 20,
            "format": "10s10s",
            "dimensions": (10, 2),
            "python_type": "list[str]",
        },
        "chars": {
            "offset": 23,
            "size": 10,
            "format": "10c",
            "dimensions": (5, 2),
            "python_type": "list[list[bytes]]",
        },
        "float64": {
            "offset": 33,
            "size": 8,
            "format": "d",
            "dimensions": None,
            "python_type": "float",
        },
        "uint16s": {
            "offset": 41,
            "size": 24,
            "format": "12H",
            "dimensions": (3, 2, 2),
            "python_type": "list[list[list[int]]]",
        },
        "child": {
            "offset": 65,
            "size": 22,
            "format": "5sH5s5sBBBBB",
            "dimensions": None,
            "python_type": "MySubStruct",
        },
        "children": {
            "offset": 87,
            "size": 44,
            "format": "5sH5s5sBBBBB5sH5s5sBBBBB",
            "dimensions": (2,),
            "python_type": "list[MySubStruct]",
        },
    }


def test_buffer_property(test_data: bytes) -> None:
    """Test the buffer property for reading and writing."""
    # Test reading buffer
    data = MyStruct(test_data)
    assert (
        data.buffer == test_data[: MyStruct._nb_bytes]
    )  # Should be limited to struct size
    verify_struct_values(data)  # Verify initial values

    # Test writing buffer - prepare new data with different values
    new_data = (
        struct.pack("<H", 54321)  # uint16
        + b"Y"  # char
        + b"Howdy\x00\x00\x00\x00\x00"  # string[10]
        + b"There\x00\x00\x00\x00\x00"  # string[10]
        + b"Howdy"  # chars[5]
        + b"There"  # chars[5]
        + struct.pack("<d", 2.71828)  # float64
        + struct.pack("<3H", 10, 20, 30)  # uint16s[3], element 0
        + struct.pack("<3H", 40, 50, 60)  # uint16s[3], element 1
        + struct.pack("<3H", 70, 80, 90)  # uint16s[3], element 2
        + struct.pack("<3H", 100, 110, 120)  # uint16s[3], element 3
        # child: MySubStruct
        + b"Mom\0\0"  # foo: string[5]
        + struct.pack("<H", 24)  # bar: uint16
        + b"qux42"  # qux[0]: string[5]
        + b"qux43"  # qux[1]: string[5]
        + struct.pack("<B", 21)  # sub.simple: MySubSubStruct
        + struct.pack("<B", 22)  # subs[0][0].simple: MySubSubStruct
        + struct.pack("<B", 23)  # subs[0][1].simple: MySubSubStruct
        + struct.pack("<B", 24)  # subs[1][0].simple: MySubSubStruct
        + struct.pack("<B", 25)  # subs[1][1].simple: MySubSubStruct
        # children: MySubStruct * 2
        # children[0]: MySubStruct
        + b"Dad\0\0"  # children[0].foo: string[5]
        + struct.pack("<H", 201)  # children[0].bar: uint16
        + b"qux44"  # children[0].qux[0]: string[5]
        + b"qux45"  # children[0].qux[1]: string[5]
        + struct.pack("<B", 26)  # children[0].sub.simple: MySubSubStruct
        + struct.pack("<B", 27)  # children[0].subs[0][0].simple: MySubSubStruct
        + struct.pack("<B", 28)  # children[0].subs[0][1].simple: MySubSubStruct
        + struct.pack("<B", 29)  # children[0].subs[1][0].simple: MySubSubStruct
        + struct.pack("<B", 30)  # children[0].subs[1][1].simple: MySubSubStruct
        # children[1]: MySubStruct
        + b"Sis\0\0"  # children[1].foo: string[5]
        + struct.pack("<H", 202)  # children[1].bar: uint16
        + b"qux46"  # children[1].qux[0]: string[5]
        + b"qux47"  # children[1].qux[1]: string[5]
        + struct.pack("<B", 31)  # children[1].sub.simple: MySubSubStruct
        + struct.pack("<B", 32)  # children[1].subs[0][0].simple: MySubSubStruct
        + struct.pack("<B", 33)  # children[1].subs[0][1].simple: MySubSubStruct
        + struct.pack("<B", 34)  # children[1].subs[1][0].simple: MySubSubStruct
        + struct.pack("<B", 35)  # children[1].subs[1][1].simple: MySubSubStruct
    )

    # Update buffer and verify values are changed
    data.buffer = new_data
    assert data.buffer == new_data[: MyStruct._nb_bytes]

    # Verify all values are updated, including sub-structs
    assert data.uint16 == 54321
    assert data.char == b"Y"
    assert data.strings == ["Howdy", "There"]
    assert data.chars == [
        [b"H", b"o", b"w", b"d", b"y"],
        [b"T", b"h", b"e", b"r", b"e"],
    ]
    assert abs(data.float64 - 2.71828) < 1e-6
    assert data.uint16s == [
        [[10, 20, 30], [40, 50, 60]],
        [[70, 80, 90], [100, 110, 120]],
    ]

    # Test child struct
    assert data.child.foo == "Mom"
    assert data.child.bar == 24
    assert data.child.qux == ["qux42", "qux43"]
    assert data.child.sub.simple == 21
    assert data.child.subs[0][0].simple == 22
    assert data.child.subs[0][1].simple == 23
    assert data.child.subs[1][0].simple == 24
    assert data.child.subs[1][1].simple == 25

    # Test children array
    assert data.children[0].foo == "Dad"
    assert data.children[0].bar == 201
    assert data.children[0].qux == ["qux44", "qux45"]
    assert data.children[0].sub.simple == 26
    assert data.children[0].subs[0][0].simple == 27
    assert data.children[0].subs[0][1].simple == 28
    assert data.children[0].subs[1][0].simple == 29
    assert data.children[0].subs[1][1].simple == 30

    assert data.children[1].foo == "Sis"
    assert data.children[1].bar == 202
    assert data.children[1].qux == ["qux46", "qux47"]
    assert data.children[1].sub.simple == 31
    assert data.children[1].subs[0][0].simple == 32
    assert data.children[1].subs[0][1].simple == 33
    assert data.children[1].subs[1][0].simple == 34
    assert data.children[1].subs[1][1].simple == 35

    # Test error cases
    with pytest.raises(ValueError, match="Buffer too small"):
        data.buffer = new_data[:-1]  # Try to set a buffer that's too small

    data.free_buffer()
    with pytest.raises(ValueError, match="No buffer available"):
        _ = data.buffer  # Try to read buffer after it's freed

    # Test at creation time with a buffer that's too small
    with pytest.raises(ValueError, match="Buffer too small"):
        MyStruct(new_data[:-1])


def test_field_writing(test_data: bytes) -> None:
    """Test writing individual fields."""
    data = MyStruct(bytearray(test_data))  # Use bytearray to make it mutable
    verify_struct_values(data)  # Verify initial values

    # Test writing basic types
    data.uint16 = 54321
    assert data.uint16 == 54321

    # Test writing single char
    data.char = b"Y"
    assert data.char == b"Y"

    # Test error on invalid char types
    with pytest.raises(TypeError, match="Expected bytes, got str"):
        data.char = "Z"  # type: ignore[assignment]

    with pytest.raises(TypeError, match="Expected bytes, got int"):
        data.char = 65  # type: ignore[assignment]

    data.float64 = 2.71828
    assert abs(data.float64 - 2.71828) < 1e-6

    # Test writing strings
    data.strings = ["Howdy", "There"]
    assert data.strings == ["Howdy", "There"]

    # Test writing chars
    data.chars = [
        [b"H", b"o", b"w", b"d", b"y"],
        [b"T", b"h", b"e", b"r", b"e"],
    ]
    assert data.chars == [
        [b"H", b"o", b"w", b"d", b"y"],
        [b"T", b"h", b"e", b"r", b"e"],
    ]

    # Test writing multi-dimensional arrays
    data.uint16s = [
        [[10, 20, 30], [40, 50, 60]],
        [[70, 80, 90], [100, 110, 120]],
    ]
    assert data.uint16s == [
        [[10, 20, 30], [40, 50, 60]],
        [[70, 80, 90], [100, 110, 120]],
    ]

    # Test writing to sub-struct fields
    data.child.foo = "Mom"
    assert data.child.foo == "Mom"

    data.child.bar = 24
    assert data.child.bar == 24

    data.child.qux = ["qux42", "qux43"]
    assert data.child.qux == ["qux42", "qux43"]

    data.child.sub.simple = 21
    assert data.child.sub.simple == 21

    # Test writing to sub-struct array fields
    data.child.subs[0][0].simple = 22
    data.child.subs[0][1].simple = 23
    data.child.subs[1][0].simple = 24
    data.child.subs[1][1].simple = 25
    assert data.child.subs[0][0].simple == 22
    assert data.child.subs[0][1].simple == 23
    assert data.child.subs[1][0].simple == 24
    assert data.child.subs[1][1].simple == 25

    # Test writing to array of sub-structs
    data.children[0].foo = "Dad"
    data.children[0].bar = 201
    data.children[0].qux = ["qux44", "qux45"]
    data.children[0].sub.simple = 26
    assert data.children[0].foo == "Dad"
    assert data.children[0].bar == 201
    assert data.children[0].qux == ["qux44", "qux45"]
    assert data.children[0].sub.simple == 26

    data.children[1].foo = "Sis"
    data.children[1].bar = 202
    data.children[1].qux = ["qux46", "qux47"]
    data.children[1].sub.simple = 31
    assert data.children[1].foo == "Sis"
    assert data.children[1].bar == 202
    assert data.children[1].qux == ["qux46", "qux47"]
    assert data.children[1].sub.simple == 31

    # Test error cases
    with pytest.raises(TypeError, match="Cannot write to immutable buffer"):
        MyStruct(test_data).uint16 = 1  # Try to write to immutable bytes buffer

    with pytest.raises(TypeError, match="Expected bytes, got str"):
        data.char = "a"  # type: ignore[assignment]  # Try to write string to char field

    with pytest.raises(TypeError, match="Expected int, got str"):
        data.uint16 = "not a number"  # type: ignore[assignment]  # Try to write invalid value type

    with pytest.raises(ValueError, match="Failed to pack value"):
        data.strings = ["Too", "Long", "String"]  # Try to write too many strings
