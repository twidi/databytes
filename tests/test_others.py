from copy import deepcopy

import pytest

from databytes import BinaryStruct
from databytes import types as t


class Child(BinaryStruct):
    field1: t.uint16
    field2: t.string[5]


class Data(BinaryStruct):
    field: t.uint16
    children: Child[2]


class DeepChild(BinaryStruct):
    value: t.uint8
    name: t.string[4]


class MiddleStruct(BinaryStruct):
    id: t.uint16
    deep_strings: t.string[5, 2, 3]  # list of 3 lists of 2 deep strings of 5 chars
    deep_children: DeepChild[2, 3]  # list of 3 lists of 2 deep children


class ComplexData(BinaryStruct):
    field: t.uint32
    middle: MiddleStruct
    extra: t.string[5]


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


def test_to_dict_simple():
    # Create and fill a Child structure
    buffer = bytearray(1000)
    child = Child(buffer)
    child.field1 = 42
    child.field2 = "Hello"

    # Test to_dict
    result = child.to_dict()
    assert result == {
        "field1": 42,
        "field2": "Hello",
    }


def test_to_dict_nested():
    # Create and fill a Data structure with nested Child structures
    buffer = bytearray(1000)
    data = Data(buffer)
    data.field = 1
    data.children[0].field1 = 2
    data.children[0].field2 = "Hello"
    data.children[1].field1 = 3
    data.children[1].field2 = "World"

    # Test to_dict
    result = data.to_dict()
    assert result == {
        "field": 1,
        "children": [
            {"field1": 2, "field2": "Hello"},
            {"field1": 3, "field2": "World"},
        ],
    }


def test_to_dict_deep_nested_and_multidim():
    # Create and fill a complex structure with 2 levels of nesting
    # and a 2D array of structures
    buffer = bytearray(1000)
    data = ComplexData(buffer)

    # Set simple fields
    data.field = 12345
    data.extra = "Test!"

    # Set middle structure fields
    data.middle.id = 42

    # Fill the 2D array of deep strings (list of 3 lists of 2 deep strings)
    data.middle.deep_strings = [
        ["s00", "s01"],
        ["s10", "s11"],
        ["s20", "s21"],
    ]

    # Fill the 2D array of deep children (list of 3 lists of 2 deep children)
    data.middle.deep_children[0][0].value = 0
    data.middle.deep_children[0][0].name = "n00"
    data.middle.deep_children[0][1].value = 1
    data.middle.deep_children[0][1].name = "n01"
    data.middle.deep_children[1][0].value = 2
    data.middle.deep_children[1][0].name = "n10"
    data.middle.deep_children[1][1].value = 3
    data.middle.deep_children[1][1].name = "n11"
    data.middle.deep_children[2][0].value = 4
    data.middle.deep_children[2][0].name = "n20"
    data.middle.deep_children[2][1].value = 5
    data.middle.deep_children[2][1].name = "n21"

    # Test to_dict
    result = data.to_dict()
    assert result == {
        "field": 12345,
        "middle": {
            "id": 42,
            "deep_strings": [
                ["s00", "s01"],
                ["s10", "s11"],
                ["s20", "s21"],
            ],
            "deep_children": [
                [
                    {"value": 0, "name": "n00"},
                    {"value": 1, "name": "n01"},
                ],
                [
                    {"value": 2, "name": "n10"},
                    {"value": 3, "name": "n11"},
                ],
                [
                    {"value": 4, "name": "n20"},
                    {"value": 5, "name": "n21"},
                ],
            ],
        },
        "extra": "Test!",
    }


def test_to_dict_strings_dimensions():
    class Single(BinaryStruct):
        value: t.string[5]

    class Array(BinaryStruct):
        value: t.string[5, 2]  # list of 2 strings of 5 chars

    class Matrix(BinaryStruct):
        strings: t.string[5, 2, 3]  # list of 3 lists of 2 strings of 5 chars

    buffer = bytearray(1000)
    single = Single(buffer)
    array = Array(buffer)
    matrix = Matrix(buffer)

    # Test to_dict
    single.value = "Hello"
    result = single.to_dict()
    assert result == {
        "value": "Hello",
    }

    array.value = ["Hello", "World"]
    result = array.to_dict()
    assert result == {
        "value": ["Hello", "World"],
    }

    matrix.strings = [
        ["s00", "s01"],
        ["s10", "s11"],
        ["s20", "s21"],
    ]
    result = matrix.to_dict()
    assert result == {
        "strings": [
            ["s00", "s01"],
            ["s10", "s11"],
            ["s20", "s21"],
        ],
    }


def test_fill_from_dict_simple():
    class Simple(BinaryStruct):
        field1: t.uint16
        field2: t.string[5]

    buffer = bytearray(1000)
    data = Simple(buffer)

    # Test filling with complete dict
    data.fill_from_dict({"field1": 42, "field2": "Hello"})
    assert data.field1 == 42
    assert data.field2 == "Hello"

    # Test filling with partial dict
    data.fill_from_dict({"field1": 24})
    assert data.field1 == 24
    assert data.field2 == "Hello"  # Should keep old value

    # Test with clear_unset=True
    data.fill_from_dict({"field1": 99}, clear_unset=True)
    assert data.field1 == 99
    assert data.field2 == ""  # Should be cleared


def test_fill_from_dict_arrays():
    class ArrayStruct(BinaryStruct):
        numbers: t.uint16[3]
        strings: t.string[5, 2]  # list of 2 strings of 5 chars

    buffer = bytearray(1000)
    data = ArrayStruct(buffer)

    data.fill_from_dict(
        {
            "numbers": [1, 2, 3],
            "strings": ["Hello", "World"],
        }
    )
    assert list(data.numbers) == [1, 2, 3]
    assert list(data.strings) == ["Hello", "World"]

    # Test with invalid dimensions
    with pytest.raises(ValueError, match="Invalid dimensions"):
        data.fill_from_dict({"numbers": [1, 2]})  # Too few items
    with pytest.raises(ValueError, match="Invalid dimensions"):
        data.fill_from_dict({"strings": ["One"]})  # Too few items
    with pytest.raises(TypeError, match="Expected list"):
        data.fill_from_dict({"numbers": "not a list"})


def test_fill_from_dict_nested():
    buffer = bytearray(1000)
    data = ComplexData(buffer)

    test_dict = {
        "field": 42,
        "middle": {
            "id": 1,
            "deep_strings": [
                ["s00", "s01"],
                ["s10", "s11"],
                ["s20", "s21"],
            ],
            "deep_children": [
                [
                    {"value": 1, "name": "n00"},
                    {"value": 2, "name": "n01"},
                ],
                [
                    {"value": 3, "name": "n10"},
                    {"value": 4, "name": "n11"},
                ],
                [
                    {"value": 5, "name": "n20"},
                    {"value": 6, "name": "n21"},
                ],
            ],
        },
        "extra": "Test!",
    }

    data.fill_from_dict(test_dict)

    # Verify all values were set correctly
    assert data.field == 42
    assert data.middle.id == 1
    assert data.extra == "Test!"

    # Check deep strings
    assert list(data.middle.deep_strings[0]) == ["s00", "s01"]
    assert list(data.middle.deep_strings[1]) == ["s10", "s11"]
    assert list(data.middle.deep_strings[2]) == ["s20", "s21"]

    # Check deep children
    assert data.middle.deep_children[0][0].value == 1
    assert data.middle.deep_children[0][0].name == "n00"
    assert data.middle.deep_children[2][1].value == 6
    assert data.middle.deep_children[2][1].name == "n21"

    # Test with invalid nested structure
    with pytest.raises(TypeError, match="Expected dict"):
        data.fill_from_dict({"middle": "not a dict"})
    with pytest.raises(ValueError, match="Invalid dimensions for field deep_children"):
        data.fill_from_dict({"middle": {"deep_children": [[["not a dict"]]]}})

    # Test something expected to be a dict for a deep nested sub-struct in array
    test_dict2 = deepcopy(test_dict)
    # just to check we target the right entry
    assert test_dict2["middle"]["deep_children"][0][0] == {"value": 1, "name": "n00"}  # type: ignore[index]
    test_dict2["middle"]["deep_children"][0][0] = "not a dict"  # type: ignore[index]
    with pytest.raises(TypeError, match="Expected dict"):
        data.fill_from_dict(test_dict2)
