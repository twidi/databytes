"""Tests for uint16 field type."""

from struct import pack

import pytest

from databytes import BinaryStruct
from databytes import types as t


def test_uint16_field() -> None:
    """Test uint16 fields with various dimensions to ensure correct memory handling."""

    class Uint16Struct(BinaryStruct):
        # Test cases for different uint16 field configurations
        single_value: t.uint16  # Single uint16 value
        value_array: t.uint16[3]  # Array of 3 uint16s
        value_matrix: t.uint16[2, 3]  # Matrix of uint16s: 3 rows of 2 values

    # Calculate buffer size: 2 + (2 * 3) + (2 * 2 * 3)
    buffer_size = (
        2  # single_value
        + (2 * 3)  # value_array
        + (2 * 2 * 3)  # value_matrix: 3 rows of 2 values each
    )
    buffer = bytearray(buffer_size)
    data = Uint16Struct(buffer)

    # Ensure buffer is all zeros
    assert buffer == t.NULL * buffer_size

    prev_buffer = bytearray(buffer)

    # Test single uint16 value
    data.single_value = 1000
    expected_content = pack("<H", 1000)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_value == 1000

    with pytest.raises(ValueError):
        data.single_value = 65536  # Too large for uint16
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.single_value = 1000  # reset

    with pytest.raises(ValueError):
        data.single_value = -1  # Negative not allowed for uint16
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.single_value = 1000  # reset

    prev_buffer = bytearray(expected_buffer)

    # Test uint16 array
    data.value_array = [10000, 20000, 30000]
    expected_content += pack("<3H", 10000, 20000, 30000)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.value_array[0] == 10000
    assert data.value_array[1] == 20000
    assert data.value_array[2] == 30000

    with pytest.raises(ValueError):
        data.value_array = [65536, 22222, 33333]  # One value too large
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_array = [10000, 20000, 30000]  # reset

    with pytest.raises(ValueError):
        data.value_array = [-1, 22222, 33333]  # Negative not allowed
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_array = [10000, 20000, 30000]  # reset

    with pytest.raises(ValueError):
        data.value_array = [10000, 22222, 33333, 44444]  # Too many values
    assert buffer == expected_buffer  # buffer not updated
    data.value_array = [10000, 20000, 30000]  # reset

    prev_buffer = bytearray(expected_buffer)

    # Test uint16 matrix
    data.value_matrix = [[1000, 2000], [3000, 4000], [5000, 6000]]
    expected_content += pack("<6H", 1000, 2000, 3000, 4000, 5000, 6000)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.value_matrix[0] == [1000, 2000]
    assert data.value_matrix[1] == [3000, 4000]
    assert data.value_matrix[2] == [5000, 6000]

    with pytest.raises(ValueError):
        data.value_matrix = [[1111, 2222], [3333, 4444]]  # Not enough rows
    assert buffer == expected_buffer  # buffer not updated

    with pytest.raises(ValueError):
        data.value_matrix = [
            [65536, 2222],
            [3333, 4444],
            [5555, 6666],
        ]  # Value too large
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_matrix = [[1000, 2000], [3000, 4000], [5000, 6000]]  # reset

    with pytest.raises(ValueError):
        data.value_matrix = [
            [-1, 2222],
            [3333, 4444],
            [5555, 6666],
        ]  # Negative not allowed
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_matrix = [[1000, 2000], [3000, 4000], [5000, 6000]]  # reset

    # Test that we can read the full buffer and verify all values
    new_data = Uint16Struct(buffer)
    assert new_data.single_value == 1000
    assert list(new_data.value_array) == [10000, 20000, 30000]
    assert new_data.value_matrix == [[1000, 2000], [3000, 4000], [5000, 6000]]
