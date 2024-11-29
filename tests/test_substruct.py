import pytest

from databytes import BinaryStruct
from databytes import types as t


class SubSubStruct(BinaryStruct):
    """A simple nested struct for testing."""

    value: t.uint16
    flag: t.bool


class SubStruct(BinaryStruct):
    """A struct containing primitive types and a nested struct."""

    name: t.string[5]  # Fixed-length string
    number: t.uint16
    nested: SubSubStruct  # Single nested struct
    nested_array: SubSubStruct[2]  # Array of nested structs
    nested_matrix: SubSubStruct[2, 2]  # Matrix of nested structs


class MainStruct(BinaryStruct):
    """Main struct for testing substruct functionality."""

    single_sub: SubStruct  # Single substruct
    sub_array: SubStruct[2]  # Array of substructs
    sub_matrix: SubStruct[2, 2]  # Matrix of substructs


def test_substruct_field() -> None:
    """Test substruct fields with various dimensions to ensure correct memory handling."""

    # Calculate buffer size for MainStruct
    # SubSubStruct size = 2 (uint16) + 1 (bool) = 3 bytes
    # SubStruct size = 5 (string[5]) + 2 (uint16) + 3 (SubSubStruct) +
    #                  (2 * 3) (nested_array) + (2 * 2 * 3) (nested_matrix) = 28 bytes
    # MainStruct size = 28 (single_sub) + (2 * 28) (sub_array) + (2 * 2 * 28) (sub_matrix)
    #                 = 28 + 56 + 112 = 196

    buffer_size = 196
    buffer = bytearray(buffer_size)
    data = MainStruct(buffer)

    # Ensure buffer is all zeros
    assert buffer == t.NULL * buffer_size

    # Test single substruct
    data.single_sub.name = "Test"
    data.single_sub.number = 42
    data.single_sub.nested.value = 123
    data.single_sub.nested.flag = True
    data.single_sub.nested_array[0].value = 1
    data.single_sub.nested_array[0].flag = True
    data.single_sub.nested_array[1].value = 2
    data.single_sub.nested_array[1].flag = False
    data.single_sub.nested_matrix[0][0].value = 11
    data.single_sub.nested_matrix[0][0].flag = True
    data.single_sub.nested_matrix[0][1].value = 12
    data.single_sub.nested_matrix[0][1].flag = False
    data.single_sub.nested_matrix[1][0].value = 13
    data.single_sub.nested_matrix[1][0].flag = True
    data.single_sub.nested_matrix[1][1].value = 14
    data.single_sub.nested_matrix[1][1].flag = False

    # Verify single substruct values
    assert data.single_sub.name == "Test"
    assert data.single_sub.number == 42
    assert data.single_sub.nested.value == 123
    assert data.single_sub.nested.flag is True
    assert data.single_sub.nested_array[0].value == 1
    assert data.single_sub.nested_array[0].flag is True
    assert data.single_sub.nested_array[1].value == 2
    assert data.single_sub.nested_array[1].flag is False
    assert data.single_sub.nested_matrix[0][0].value == 11
    assert data.single_sub.nested_matrix[0][0].flag is True
    assert data.single_sub.nested_matrix[0][1].value == 12
    assert data.single_sub.nested_matrix[0][1].flag is False
    assert data.single_sub.nested_matrix[1][0].value == 13
    assert data.single_sub.nested_matrix[1][0].flag is True
    assert data.single_sub.nested_matrix[1][1].value == 14
    assert data.single_sub.nested_matrix[1][1].flag is False

    # Test array of substructs
    for i in range(2):
        data.sub_array[i].name = f"Arr{i}"
        data.sub_array[i].number = i + 100
        data.sub_array[i].nested.value = i + 50
        data.sub_array[i].nested.flag = bool(i)
        for j in range(2):
            data.sub_array[i].nested_array[j].value = i * 10 + j
            data.sub_array[i].nested_array[j].flag = bool((i + j) % 2)
            for k in range(2):
                data.sub_array[i].nested_matrix[j][k].value = i * 100 + j * 10 + k
                data.sub_array[i].nested_matrix[j][k].flag = bool((i + j + k) % 2)

    # Verify array of substructs
    for i in range(2):
        assert data.sub_array[i].name == f"Arr{i}"
        assert data.sub_array[i].number == i + 100
        assert data.sub_array[i].nested.value == i + 50
        assert data.sub_array[i].nested.flag is bool(i)
        for j in range(2):
            assert data.sub_array[i].nested_array[j].value == i * 10 + j
            assert data.sub_array[i].nested_array[j].flag is bool((i + j) % 2)
            for k in range(2):
                assert data.sub_array[i].nested_matrix[j][k].value == i * 100 + j * 10 + k
                assert data.sub_array[i].nested_matrix[j][k].flag is bool((i + j + k) % 2)

    # Test matrix of substructs
    for i in range(2):
        for j in range(2):
            data.sub_matrix[i][j].name = f"M{i}{j}"
            data.sub_matrix[i][j].number = i * 1000 + j * 100
            data.sub_matrix[i][j].nested.value = i * 10 + j
            data.sub_matrix[i][j].nested.flag = bool((i + j) % 2)
            for k in range(2):
                data.sub_matrix[i][j].nested_array[k].value = i * 100 + j * 10 + k
                data.sub_matrix[i][j].nested_array[k].flag = bool((i + j + k) % 2)
                for l in range(2):  # noqa: E741
                    data.sub_matrix[i][j].nested_matrix[k][l].value = i * 1000 + j * 100 + k * 10 + l
                    data.sub_matrix[i][j].nested_matrix[k][l].flag = bool((i + j + k + l) % 2)

    # Verify matrix of substructs
    for i in range(2):
        for j in range(2):
            assert data.sub_matrix[i][j].name == f"M{i}{j}"
            assert data.sub_matrix[i][j].number == i * 1000 + j * 100
            assert data.sub_matrix[i][j].nested.value == i * 10 + j
            assert data.sub_matrix[i][j].nested.flag is bool((i + j) % 2)
            for k in range(2):
                assert data.sub_matrix[i][j].nested_array[k].value == i * 100 + j * 10 + k
                assert data.sub_matrix[i][j].nested_array[k].flag is bool((i + j + k) % 2)
                for l in range(2):  # noqa: E741
                    assert data.sub_matrix[i][j].nested_matrix[k][l].value == i * 1000 + j * 100 + k * 10 + l
                    assert data.sub_matrix[i][j].nested_matrix[k][l].flag is bool((i + j + k + l) % 2)

    # Test error handling
    with pytest.raises(ValueError):
        data.single_sub.name = "TooLong"  # String too long for string[5]

    # Test that we can read the full buffer with a new instance
    new_data = MainStruct(buffer)

    # Verify single substruct values in new instance
    assert new_data.single_sub.name == "Test"
    assert new_data.single_sub.number == 42
    assert new_data.single_sub.nested.value == 123
    assert new_data.single_sub.nested.flag is True

    # Verify array values in new instance (checking first element as example)
    assert new_data.sub_array[0].name == "Arr0"
    assert new_data.sub_array[0].number == 100
    assert new_data.sub_array[0].nested.value == 50
    assert new_data.sub_array[0].nested.flag is False

    # Verify matrix values in new instance (checking first element as example)
    assert new_data.sub_matrix[0][0].name == "M00"
    assert new_data.sub_matrix[0][0].number == 0
    assert new_data.sub_matrix[0][0].nested.value == 0
    assert new_data.sub_matrix[0][0].nested.flag is False
