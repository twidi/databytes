"""Tests for int8 field type."""

from struct import pack

import pytest

from databytes import BinaryStruct
from databytes import types as t


def test_int8_field() -> None:
    """Test int8 fields with various dimensions to ensure correct memory handling."""

    class Int8Struct(BinaryStruct):
        # Test cases for different int8 field configurations
        single_value: t.int8  # Single int8 value
        value_array: t.int8[3]  # Array of 3 int8s
        value_matrix: t.int8[2, 3]  # Matrix of int8s: 3 rows of 2 values

    # Calculate buffer size: 1 + 3 + (2 * 3)
    buffer_size = (
        1  # single_value
        + 3  # value_array
        + (2 * 3)  # value_matrix: 3 rows of 2 values each
    )
    buffer = bytearray(buffer_size)
    data = Int8Struct(buffer)

    # Ensure buffer is all zeros
    assert buffer == t.NULL * buffer_size

    prev_buffer = bytearray(buffer)

    # Test single int8 value
    data.single_value = 42
    expected_content = bytes([42])
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_value == 42

    data.single_value = -42  # Test negative value
    expected_content = pack("<b", -42)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_value == -42

    with pytest.raises(ValueError):
        data.single_value = 128  # Too large for int8
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.single_value = -42  # reset

    with pytest.raises(ValueError):
        data.single_value = -129  # Too small for int8
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.single_value = -42  # reset

    prev_buffer = bytearray(expected_buffer)

    # Test int8 array
    data.value_array = [-10, 20, -30]
    expected_content += pack("<3b", -10, 20, -30)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.value_array[0] == -10
    assert data.value_array[1] == 20
    assert data.value_array[2] == -30

    with pytest.raises(ValueError):
        data.value_array = [128, 22, 33]  # One value too large
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_array = [-10, 20, -30]  # reset

    with pytest.raises(ValueError):
        data.value_array = [-129, 22, 33]  # One value too small
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_array = [-10, 20, -30]  # reset

    with pytest.raises(ValueError):
        data.value_array = [11, 22, 33, 44]  # Too many values
    assert buffer == expected_buffer  # buffer not updated
    data.value_array = [-10, 20, -30]  # reset

    prev_buffer = bytearray(expected_buffer)

    # Test int8 matrix
    data.value_matrix = [[-1, 2], [-3, 4], [-5, 6]]
    expected_content += pack("<6b", -1, 2, -3, 4, -5, 6)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.value_matrix[0] == [-1, 2]
    assert data.value_matrix[1] == [-3, 4]
    assert data.value_matrix[2] == [-5, 6]

    with pytest.raises(ValueError):
        data.value_matrix = [[11, 22], [33, 44]]  # Not enough rows
    assert buffer == expected_buffer  # buffer not updated

    with pytest.raises(ValueError):
        data.value_matrix = [[128, 22], [33, 44], [55, 66]]  # Value too large
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_matrix = [[-1, 2], [-3, 4], [-5, 6]]  # reset

    with pytest.raises(ValueError):
        data.value_matrix = [[-129, 22], [33, 44], [55, 66]]  # Value too small
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_matrix = [[-1, 2], [-3, 4], [-5, 6]]  # reset

    # Test that we can read the full buffer and verify all values
    new_data = Int8Struct(buffer)
    assert new_data.single_value == -42
    assert list(new_data.value_array) == [-10, 20, -30]
    assert new_data.value_matrix == [[-1, 2], [-3, 4], [-5, 6]]
