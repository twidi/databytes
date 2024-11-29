"""Tests for int32 field type."""

from struct import pack

import pytest

from databytes import BinaryStruct
from databytes import types as t


def test_int32_field() -> None:
    """Test int32 fields with various dimensions to ensure correct memory handling."""

    class Int32Struct(BinaryStruct):
        # Test cases for different int32 field configurations
        single_value: t.int32  # Single int32 value
        value_array: t.int32[3]  # Array of 3 int32s
        value_matrix: t.int32[2, 3]  # Matrix of int32s: 3 rows of 2 values

    # Calculate buffer size: 4 + (4 * 3) + (4 * 2 * 3)
    buffer_size = (
        4  # single_value
        + (4 * 3)  # value_array
        + (4 * 2 * 3)  # value_matrix: 3 rows of 2 values each
    )
    buffer = bytearray(buffer_size)
    data = Int32Struct(buffer)

    # Ensure buffer is all zeros
    assert buffer == t.NULL * buffer_size

    prev_buffer = bytearray(buffer)

    # Test single int32 value
    data.single_value = 1_000_000
    expected_content = pack("<i", 1_000_000)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_value == 1_000_000

    data.single_value = -1_000_000  # Test negative value
    expected_content = pack("<i", -1_000_000)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_value == -1_000_000

    with pytest.raises(ValueError):
        data.single_value = 2_147_483_648  # Too large for int32
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.single_value = -1_000_000  # reset

    with pytest.raises(ValueError):
        data.single_value = -2_147_483_649  # Too small for int32
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.single_value = -1_000_000  # reset

    prev_buffer = bytearray(expected_buffer)

    # Test int32 array
    data.value_array = [-1_000_000, 2_000_000, -3_000_000]
    expected_content += pack("<3i", -1_000_000, 2_000_000, -3_000_000)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.value_array[0] == -1_000_000
    assert data.value_array[1] == 2_000_000
    assert data.value_array[2] == -3_000_000

    with pytest.raises(ValueError):
        data.value_array = [2_147_483_648, 2_222_222, -3_333_333]  # One value too large
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_array = [-1_000_000, 2_000_000, -3_000_000]  # reset

    with pytest.raises(ValueError):
        data.value_array = [
            -2_147_483_649,
            2_222_222,
            -3_333_333,
        ]  # One value too small
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_array = [-1_000_000, 2_000_000, -3_000_000]  # reset

    with pytest.raises(ValueError):
        data.value_array = [
            -1_111_111,
            2_222_222,
            -3_333_333,
            4_444_444,
        ]  # Too many values
    assert buffer == expected_buffer  # buffer not updated
    data.value_array = [-1_000_000, 2_000_000, -3_000_000]  # reset

    prev_buffer = bytearray(expected_buffer)

    # Test int32 matrix
    data.value_matrix = [[-100_000, 200_000], [-300_000, 400_000], [-500_000, 600_000]]
    expected_content += pack("<6i", -100_000, 200_000, -300_000, 400_000, -500_000, 600_000)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.value_matrix[0] == [-100_000, 200_000]
    assert data.value_matrix[1] == [-300_000, 400_000]
    assert data.value_matrix[2] == [-500_000, 600_000]

    with pytest.raises(ValueError):
        data.value_matrix = [
            [-111_111, 222_222],
            [-333_333, 444_444],
        ]  # Not enough rows
    assert buffer == expected_buffer  # buffer not updated

    with pytest.raises(ValueError):
        data.value_matrix = [
            [2_147_483_648, 222_222],
            [-333_333, 444_444],
            [-555_555, 666_666],
        ]  # Value too large
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_matrix = [
        [-100_000, 200_000],
        [-300_000, 400_000],
        [-500_000, 600_000],
    ]  # reset

    with pytest.raises(ValueError):
        data.value_matrix = [
            [-2_147_483_649, 222_222],
            [-333_333, 444_444],
            [-555_555, 666_666],
        ]  # Value too small
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_matrix = [
        [-100_000, 200_000],
        [-300_000, 400_000],
        [-500_000, 600_000],
    ]  # reset

    # Test that we can read the full buffer and verify all values
    new_data = Int32Struct(buffer)
    assert new_data.single_value == -1_000_000
    assert list(new_data.value_array) == [-1_000_000, 2_000_000, -3_000_000]
    assert new_data.value_matrix == [
        [-100_000, 200_000],
        [-300_000, 400_000],
        [-500_000, 600_000],
    ]
