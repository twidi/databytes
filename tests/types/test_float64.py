"""Tests for float64 field type."""

import math
from struct import pack

import pytest

from databytes import BinaryStruct
from databytes import types as t


def test_float64_field() -> None:
    """Test float64 fields with various dimensions to ensure correct memory handling."""

    class Float64Struct(BinaryStruct):
        # Test cases for different float64 field configurations
        single_value: t.float64  # Single float64 value
        value_array: t.float64[3]  # Array of float64s
        value_matrix: t.float64[2, 3]  # Matrix of float64s: 3 rows of 2 values

    # Calculate buffer size: 8 + (8 * 3) + (8 * 2 * 3)
    buffer_size = (
        8  # single_value
        + (8 * 3)  # value_array
        + (8 * 2 * 3)  # value_matrix: 3 rows of 2 values each
    )
    buffer = bytearray(buffer_size)
    data = Float64Struct(buffer)

    # Ensure buffer is all zeros
    assert buffer == t.NULL * buffer_size

    # Test single float64 value
    data.single_value = 3.141592653589793
    expected_content = pack("<d", 3.141592653589793)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert abs(data.single_value - 3.141592653589793) < 1e-15  # Float comparison with epsilon

    # Test special values
    data.single_value = float("inf")
    expected_content = pack("<d", float("inf"))
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert math.isinf(data.single_value) and data.single_value > 0

    data.single_value = float("-inf")
    expected_content = pack("<d", float("-inf"))
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert math.isinf(data.single_value) and data.single_value < 0

    data.single_value = float("nan")
    assert math.isnan(data.single_value)

    # Reset to a normal value for further tests
    data.single_value = 3.141592653589793
    expected_content = pack("<d", 3.141592653589793)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer

    # Test float64 array
    data.value_array = [-3.141592653589793, 2.718281828459045, 1.414213562373095]
    expected_content += pack("<3d", -3.141592653589793, 2.718281828459045, 1.414213562373095)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert abs(data.value_array[0] - (-3.141592653589793)) < 1e-15
    assert abs(data.value_array[1] - 2.718281828459045) < 1e-15
    assert abs(data.value_array[2] - 1.414213562373095) < 1e-15

    # Test array with special values
    data.value_array = [float("inf"), float("-inf"), float("nan")]
    assert math.isinf(data.value_array[0]) and data.value_array[0] > 0
    assert math.isinf(data.value_array[1]) and data.value_array[1] < 0
    assert math.isnan(data.value_array[2])

    # Reset array for matrix test
    data.value_array = [-3.141592653589793, 2.718281828459045, 1.414213562373095]

    with pytest.raises(ValueError):
        data.value_array = [
            -3.141592653589793,
            2.718281828459045,
            1.414213562373095,
            1.732050807568877,
        ]  # Too many values
    assert buffer == expected_buffer  # buffer not updated
    data.value_array = [
        -3.141592653589793,
        2.718281828459045,
        1.414213562373095,
    ]  # reset

    # Test float64 matrix with more precise values
    data.value_matrix = [
        [-1.234567890123456, 2.345678901234567],
        [-3.456789012345678, 4.567890123456789],
        [-5.678901234567890, 6.789012345678901],
    ]
    expected_content += pack(
        "<6d",
        -1.234567890123456,
        2.345678901234567,
        -3.456789012345678,
        4.567890123456789,
        -5.678901234567890,
        6.789012345678901,
    )
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    for i in range(3):
        for j in range(2):
            assert (
                abs(
                    data.value_matrix[i][j]
                    - [
                        -1.234567890123456,
                        2.345678901234567,
                        -3.456789012345678,
                        4.567890123456789,
                        -5.678901234567890,
                        6.789012345678901,
                    ][i * 2 + j]
                )
                < 1e-14
            )

    with pytest.raises(ValueError):
        data.value_matrix = [
            [-1.234567890123456, 2.345678901234567],
            [-3.456789012345678, 4.567890123456789],
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
        [-1.234567890123456, 2.345678901234567],
        [-3.456789012345678, 4.567890123456789],
        [-5.678901234567890, 6.789012345678901],
    ]

    # Test that we can read the full buffer and verify all values
    new_data = Float64Struct(buffer)
    assert abs(new_data.single_value - 3.141592653589793) < 1e-15
    for i, val in enumerate([-3.141592653589793, 2.718281828459045, 1.414213562373095]):
        assert abs(new_data.value_array[i] - val) < 1e-15
    for i in range(3):
        for j in range(2):
            assert (
                abs(
                    new_data.value_matrix[i][j]
                    - [
                        -1.234567890123456,
                        2.345678901234567,
                        -3.456789012345678,
                        4.567890123456789,
                        -5.678901234567890,
                        6.789012345678901,
                    ][i * 2 + j]
                )
                < 1e-14
            )
