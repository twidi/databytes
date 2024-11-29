"""Tests for int64 field type."""

from struct import pack

import pytest

from databytes import BinaryStruct
from databytes import types as t


def test_int64_field() -> None:
    """Test int64 fields with various dimensions to ensure correct memory handling."""

    class Int64Struct(BinaryStruct):
        # Test cases for different int64 field configurations
        single_value: t.int64  # Single int64 value
        value_array: t.int64[3]  # Array of int64s
        value_matrix: t.int64[2, 3]  # Matrix of int64s: 3 rows of 2 values

    # Calculate buffer size: 8 + (8 * 3) + (8 * 2 * 3)
    buffer_size = (
        8  # single_value
        + (8 * 3)  # value_array
        + (8 * 2 * 3)  # value_matrix: 3 rows of 2 values each
    )
    buffer = bytearray(buffer_size)
    data = Int64Struct(buffer)

    # Ensure buffer is all zeros
    assert buffer == t.NULL * buffer_size

    prev_buffer = bytearray(buffer)

    # Test single int64 value
    data.single_value = 1_000_000_000_000
    expected_content = pack("<q", 1_000_000_000_000)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_value == 1_000_000_000_000

    data.single_value = -1_000_000_000_000  # Test negative value
    expected_content = pack("<q", -1_000_000_000_000)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_value == -1_000_000_000_000

    with pytest.raises(ValueError):
        data.single_value = 9_223_372_036_854_775_808  # Too large for int64
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.single_value = -1_000_000_000_000  # reset

    with pytest.raises(ValueError):
        data.single_value = -9_223_372_036_854_775_809  # Too small for int64
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.single_value = -1_000_000_000_000  # reset

    prev_buffer = bytearray(expected_buffer)

    # Test int64 array
    data.value_array = [-1_000_000_000_000, 2_000_000_000_000, -3_000_000_000_000]
    expected_content += pack("<3q", -1_000_000_000_000, 2_000_000_000_000, -3_000_000_000_000)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.value_array[0] == -1_000_000_000_000
    assert data.value_array[1] == 2_000_000_000_000
    assert data.value_array[2] == -3_000_000_000_000

    with pytest.raises(ValueError):
        data.value_array = [
            9_223_372_036_854_775_808,
            2_222_222_222_222,
            -3_333_333_333_333,
        ]  # One value too large
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_array = [
        -1_000_000_000_000,
        2_000_000_000_000,
        -3_000_000_000_000,
    ]  # reset

    with pytest.raises(ValueError):
        data.value_array = [
            -9_223_372_036_854_775_809,
            2_222_222_222_222,
            -3_333_333_333_333,
        ]  # One value too small
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_array = [
        -1_000_000_000_000,
        2_000_000_000_000,
        -3_000_000_000_000,
    ]  # reset

    with pytest.raises(ValueError):
        data.value_array = [
            -1_111_111_111_111,
            2_222_222_222_222,
            -3_333_333_333_333,
            4_444_444_444_444,
        ]  # Too many values
    assert buffer == expected_buffer  # buffer not updated
    data.value_array = [
        -1_000_000_000_000,
        2_000_000_000_000,
        -3_000_000_000_000,
    ]  # reset

    prev_buffer = bytearray(expected_buffer)

    # Test int64 matrix
    data.value_matrix = [
        [-100_000_000_000, 200_000_000_000],
        [-300_000_000_000, 400_000_000_000],
        [-500_000_000_000, 600_000_000_000],
    ]
    expected_content += pack(
        "<6q",
        -100_000_000_000,
        200_000_000_000,
        -300_000_000_000,
        400_000_000_000,
        -500_000_000_000,
        600_000_000_000,
    )
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.value_matrix[0] == [-100_000_000_000, 200_000_000_000]
    assert data.value_matrix[1] == [-300_000_000_000, 400_000_000_000]
    assert data.value_matrix[2] == [-500_000_000_000, 600_000_000_000]

    with pytest.raises(ValueError):
        data.value_matrix = [
            [-111_111_111_111, 222_222_222_222],
            [-333_333_333_333, 444_444_444_444],
        ]  # Not enough rows
    assert buffer == expected_buffer  # buffer not updated

    with pytest.raises(ValueError):
        data.value_matrix = [
            [9_223_372_036_854_775_808, 222_222_222_222],
            [-333_333_333_333, 444_444_444_444],
            [-555_555_555_555, 666_666_666_666],
        ]  # Value too large
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_matrix = [
        [-100_000_000_000, 200_000_000_000],
        [-300_000_000_000, 400_000_000_000],
        [-500_000_000_000, 600_000_000_000],
    ]  # reset

    with pytest.raises(ValueError):
        data.value_matrix = [
            [-9_223_372_036_854_775_809, 222_222_222_222],
            [-333_333_333_333, 444_444_444_444],
            [-555_555_555_555, 666_666_666_666],
        ]  # Value too small
    assert buffer == prev_buffer  # overflow still updates the buffer !
    data.value_matrix = [
        [-100_000_000_000, 200_000_000_000],
        [-300_000_000_000, 400_000_000_000],
        [-500_000_000_000, 600_000_000_000],
    ]  # reset

    # Test that we can read the full buffer and verify all values
    new_data = Int64Struct(buffer)
    assert new_data.single_value == -1_000_000_000_000
    assert list(new_data.value_array) == [
        -1_000_000_000_000,
        2_000_000_000_000,
        -3_000_000_000_000,
    ]
    assert new_data.value_matrix == [
        [-100_000_000_000, 200_000_000_000],
        [-300_000_000_000, 400_000_000_000],
        [-500_000_000_000, 600_000_000_000],
    ]
