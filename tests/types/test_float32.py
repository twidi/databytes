"""Tests for float32 field type."""

import math
from struct import pack

import pytest

from databytes import BinaryStruct
from databytes import types as t


def test_float32_field() -> None:
    """Test float32 fields with various dimensions to ensure correct memory handling."""

    class Float32Struct(BinaryStruct):
        # Test cases for different float32 field configurations
        single_value: t.float32  # Single float32 value
        value_array: t.float32[3]  # Array of float32s
        value_matrix: t.float32[2, 3]  # Matrix of float32s: 3 rows of 2 values

    # Calculate buffer size: 4 + (4 * 3) + (4 * 2 * 3)
    buffer_size = (
        4  # single_value
        + (4 * 3)  # value_array
        + (4 * 2 * 3)  # value_matrix: 3 rows of 2 values each
    )
    buffer = bytearray(buffer_size)
    data = Float32Struct(buffer)

    # Ensure buffer is all zeros
    assert buffer == t.NULL * buffer_size

    # Test single float32 value
    data.single_value = 3.14159
    expected_content = pack("<f", 3.14159)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert abs(data.single_value - 3.14159) < 1e-6  # Float comparison with epsilon

    # Test special values
    data.single_value = float("inf")
    expected_content = pack("<f", float("inf"))
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert math.isinf(data.single_value) and data.single_value > 0

    data.single_value = float("-inf")
    expected_content = pack("<f", float("-inf"))
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert math.isinf(data.single_value) and data.single_value < 0

    data.single_value = float("nan")
    assert math.isnan(data.single_value)

    # Reset to a normal value for further tests
    data.single_value = 3.14159
    expected_content = pack("<f", 3.14159)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer

    # Test float32 array
    data.value_array = [-3.14159, 2.71828, 1.41421]
    expected_content += pack("<3f", -3.14159, 2.71828, 1.41421)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert abs(data.value_array[0] - (-3.14159)) < 1e-6
    assert abs(data.value_array[1] - 2.71828) < 1e-6
    assert abs(data.value_array[2] - 1.41421) < 1e-6

    # Test array with special values
    data.value_array = [float("inf"), float("-inf"), float("nan")]
    assert math.isinf(data.value_array[0]) and data.value_array[0] > 0
    assert math.isinf(data.value_array[1]) and data.value_array[1] < 0
    assert math.isnan(data.value_array[2])

    # Reset array for matrix test
    data.value_array = [-3.14159, 2.71828, 1.41421]

    with pytest.raises(ValueError):
        data.value_array = [-3.14159, 2.71828, 1.41421, 1.73205]  # Too many values
    assert buffer == expected_buffer  # buffer not updated
    data.value_array = [-3.14159, 2.71828, 1.41421]  # reset

    # Test float32 matrix
    data.value_matrix = [
        [-1.23456, 2.34567],
        [-3.45678, 4.56789],
        [-5.67890, 6.78901],
    ]
    expected_content += pack(
        "<6f",
        -1.23456,
        2.34567,
        -3.45678,
        4.56789,
        -5.67890,
        6.78901,
    )
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    for i in range(3):
        for j in range(2):
            assert (
                abs(data.value_matrix[i][j] - [-1.23456, 2.34567, -3.45678, 4.56789, -5.67890, 6.78901][i * 2 + j])
                < 1e-5
            )

    with pytest.raises(ValueError):
        data.value_matrix = [
            [-1.23456, 2.34567],
            [-3.45678, 4.56789],
        ]  # Not enough rows
    assert buffer == expected_buffer  # buffer not updated

    # Test matrix with special values
    data.value_matrix = [
        [float("inf"), float("-inf")],
        [float("nan"), float("inf")],
        [float("-inf"), float("nan")],
    ]
    assert math.isinf(data.value_matrix[0][0]) and data.value_matrix[0][0] > 0
    assert math.isinf(data.value_matrix[0][1]) and data.value_matrix[0][1] < 0
    assert math.isnan(data.value_matrix[1][0])
    assert math.isinf(data.value_matrix[1][1]) and data.value_matrix[1][1] > 0
    assert math.isinf(data.value_matrix[2][0]) and data.value_matrix[2][0] < 0
    assert math.isnan(data.value_matrix[2][1])

    # Reset matrix to normal values
    data.value_matrix = [
        [-1.23456, 2.34567],
        [-3.45678, 4.56789],
        [-5.67890, 6.78901],
    ]

    # Test that we can read the full buffer and verify all values
    new_data = Float32Struct(buffer)
    assert abs(new_data.single_value - 3.14159) < 1e-6
    for i, val in enumerate([-3.14159, 2.71828, 1.41421]):
        assert abs(new_data.value_array[i] - val) < 1e-6
    for i in range(3):
        for j in range(2):
            assert (
                abs(new_data.value_matrix[i][j] - [-1.23456, 2.34567, -3.45678, 4.56789, -5.67890, 6.78901][i * 2 + j])
                < 1e-5
            )
