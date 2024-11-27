import struct
import sys
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path

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
    assert data.strings == ["Hello", "World"]
    assert data.chars == [[b"H", b"e", b"l", b"l", b"o"], [b"W", b"o", b"r", b"l", b"d"]]
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

    # MySubStruct layout
    assert MySubStruct._nb_bytes == 22  # 5 + 2 + (5*2) + 1 + (1*2*2)

    # MyStruct layout
    expected_size = (
        2  # uint16
        + (10 * 2)  # strings
        + (5 * 2)  # chars
        + 8  # float64
        + (2 * 3 * 2 * 2)  # uint16s
        + 22  # child (MySubStruct)
        + (22 * 2)  # children (MySubStruct[2])
    )
    assert MyStruct._nb_bytes == expected_size
