"""Tests for string field type."""

import pytest

from databytes import BinaryStruct
from databytes import types as t


def test_string_field() -> None:
    """Test string fields with various dimensions to ensure correct memory handling."""

    class StringStruct(BinaryStruct):
        # Test cases for different string field configurations
        single_char: t.string  # Single character string
        fixed_str: t.string[5]  # Fixed-length string
        str_array: t.string[3, 2]  # Array of 2 strings of 3 chars
        str_matrix: t.string[2, 3, 2]  # Matrix of strings (2 rows of 3 strings of 2 chars)

    # Calculate buffer size: 1 + 5 + (3 * 2) + (2 * 3)
    buffer_size = (
        1  # single_char
        + 5  # fixed_str
        + (3 * 2)  # str_array: 2 strings of 3 chars each
        + (2 * 3 * 2)  # str_matrix: 2 rows of 3 strings of 2 chars each
    )
    buffer = bytearray(buffer_size)
    data = StringStruct(buffer)

    # Ensure buffer is all zeros
    assert buffer == t.NULL * buffer_size

    # Test single character field
    data.single_char = "A"
    expected_content = b"A"
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_char == "A"

    with pytest.raises(ValueError):
        data.single_char = "Too long"
    assert buffer == expected_buffer  # buffer not updated

    prev_content = expected_content

    # Test fixed-length string field
    data.fixed_str = "Hello"
    expected_content = prev_content + b"Hello"
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.fixed_str == "Hello"

    data.fixed_str = "Hi"  # Shorter string should work
    expected_content = prev_content + b"Hi\0\0\0"
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.fixed_str == "Hi"

    with pytest.raises(ValueError):
        data.fixed_str = "Too long string"
    assert buffer == expected_buffer  # buffer not updated

    # Test array of strings
    data.str_array = ["ABC", "DEF"]
    expected_content += b"ABCDEF"
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.str_array == ["ABC", "DEF"]

    with pytest.raises(ValueError):
        data.str_array = ["Too long string", "Another"]
    assert buffer == expected_buffer  # buffer not updated
    with pytest.raises(ValueError):
        data.str_array = ["ABC", "DEF", "Extra"]  # Too many strings
    assert buffer == expected_buffer  # buffer not updated

    # Test character matrix
    data.str_matrix = [["A", "B", "C"], ["D", "E", "F"]]
    expected_content += b"A\0B\0C\0D\0E\0F\0"
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.str_matrix == [["A", "B", "C"], ["D", "E", "F"]]

    with pytest.raises(ValueError):
        data.str_matrix = [["A", "B"], ["C", "D"]]  # Not enough chars
    assert buffer == expected_buffer  # buffer not updated

    with pytest.raises(ValueError):
        data.str_matrix = [["AAA", "B", "C"], ["D", "E", "F"]]  # Too many chars
    assert buffer == expected_buffer  # buffer not updated

    # Test that we can read the full buffer and verify all values
    new_data = StringStruct(buffer)
    assert new_data.single_char == "A"
    assert new_data.fixed_str == "Hi"
    assert new_data.str_array == ["ABC", "DEF"]
    assert new_data.str_matrix == [["A", "B", "C"], ["D", "E", "F"]]
