"""Tests for char field type."""

import pytest

from databytes import BinaryStruct
from databytes import types as t


def test_char_field() -> None:
    """Test char fields with various dimensions to ensure correct memory handling."""

    class CharStruct(BinaryStruct):
        # Test cases for different char field configurations
        single_char: t.char  # Single character
        char_array: t.char[3]  # Array of 3 chars
        char_matrix: t.char[2, 3]  # Matrix of chars: 3 rows of 2 chars

    # Calculate buffer size: 1 + 3 + (2 * 3)
    buffer_size = (
        1  # single_char
        + 3  # char_array
        + (2 * 3)  # char_matrix: 3 rows of 2 chars each
    )
    buffer = bytearray(buffer_size)
    data = CharStruct(buffer)

    # Ensure buffer is all zeros
    assert buffer == t.NULL * buffer_size

    # Test single character field
    data.single_char = b"A"
    expected_content = b"A"
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_char == b"A"

    with pytest.raises(ValueError):
        data.single_char = b"Too long"
    assert buffer == expected_buffer  # buffer not updated

    # Test char array
    data.char_array = [b"A", b"B", b"C"]
    expected_content += b"ABC"
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.char_array[0] == b"A"
    assert data.char_array[1] == b"B"
    assert data.char_array[2] == b"C"

    with pytest.raises(ValueError):
        data.char_array = [b"Z", b"YX", b"W"]  # One element too long
    assert buffer == expected_buffer  # buffer not updated

    with pytest.raises(ValueError):
        data.char_array = [b"Z", b"Y", b"X", b"W"]  # Too many elements
    assert buffer == expected_buffer  # buffer not updated

    # Test char matrix
    data.char_matrix = [[b"A", b"B"], [b"C", b"D"], [b"E", b"F"]]
    expected_content += b"ABCDEF"
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.char_matrix[0] == [b"A", b"B"]
    assert data.char_matrix[1] == [b"C", b"D"]
    assert data.char_matrix[2] == [b"E", b"F"]

    with pytest.raises(ValueError):
        data.char_matrix = [[b"Z", b"Y"], [b"X", b"W"]]  # Not enough rows
    assert buffer == expected_buffer  # buffer not updated

    with pytest.raises(ValueError):
        data.char_matrix = [
            [b"ZY", b"X"],
            [b"W", b"V"],
            [b"U", b"T"],
        ]  # Element too long
    assert buffer == expected_buffer  # buffer not updated

    # Test that we can read the full buffer and verify all values
    new_data = CharStruct(buffer)
    assert new_data.single_char == b"A"
    assert list(new_data.char_array) == [b"A", b"B", b"C"]
    assert new_data.char_matrix == [[b"A", b"B"], [b"C", b"D"], [b"E", b"F"]]
