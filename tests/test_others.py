import pytest

from databytes import BinaryStruct
from databytes import types as t


class Child(BinaryStruct):
    field1: t.uint16
    field2: t.string[5]


class Data(BinaryStruct):
    field: t.uint16
    children: Child[2]


def test_fill_from_complete_structure():
    # Create and fill first structure
    buffer1 = bytearray(1000)
    data1 = Data(buffer1)
    data1.field = 1
    data1.children[0].field1 = 2
    data1.children[0].field2 = "Hello"
    data1.children[1].field1 = 3
    data1.children[1].field2 = "World"

    # Create second structure and fill from first
    buffer2 = bytearray(1000)
    data2 = Data(buffer2)
    data2.fill_from(data1)

    # Check all values were copied correctly
    assert data2.field == 1
    assert data2.children[0].field1 == 2
    assert data2.children[0].field2 == "Hello"
    assert data2.children[1].field1 == 3
    assert data2.children[1].field2 == "World"


def test_fill_from_sub_structure():
    # Create and fill first structure
    buffer1 = bytearray(1000)
    data1 = Data(buffer1)
    data1.field = 1
    data1.children[0].field1 = 2
    data1.children[0].field2 = "Hello"
    data1.children[1].field1 = 3
    data1.children[1].field2 = "World"

    # Create second structure and fill a sub-struct from first
    buffer2 = bytearray(1000)
    data2 = Data(buffer2)
    data2.children[1].fill_from(data1.children[0])

    # Check values were copied correctly
    assert data2.children[1].field1 == 2
    assert data2.children[1].field2 == "Hello"


def test_fill_from_incompatible_structure():
    class OtherStruct(BinaryStruct):
        field: t.uint32

    buffer1 = bytearray(1000)
    data1 = Data(buffer1)

    buffer2 = bytearray(1000)
    other = OtherStruct(buffer2)

    with pytest.raises(ValueError):
        data1.fill_from(other)  # type: ignore[arg-type]


def test_fill_from_none():
    buffer = bytearray(1000)
    data = Data(buffer)

    with pytest.raises(ValueError):
        data.fill_from(None)  # type: ignore[arg-type]
