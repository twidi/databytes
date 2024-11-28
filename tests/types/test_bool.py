"""Tests for bool field type."""

from struct import pack

import pytest

from databytes import BinaryStruct
from databytes import types as t


def test_bool_field() -> None:
    """Test bool fields with various dimensions to ensure correct memory handling."""

    class BoolStruct(BinaryStruct):
        # Test cases for different bool field configurations
        single_value: t.bool  # Single bool value
        value_array: t.bool[3]  # Array of bools
        value_matrix: t.bool[2, 3]  # Matrix of bools: 3 rows of 2 values

    # Calculate buffer size: 1 + (1 * 3) + (1 * 2 * 3)
    buffer_size = (
        1  # single_value
        + (1 * 3)  # value_array
        + (1 * 2 * 3)  # value_matrix: 3 rows of 2 values each
    )
    buffer = bytearray(buffer_size)
    data = BoolStruct(buffer)

    # Ensure buffer is all zeros
    assert buffer == t.NULL * buffer_size

    # Test single bool value
    data.single_value = True
    expected_content = pack("<?", True)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_value is True

    data.single_value = False
    expected_content = pack("<?", False)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.single_value is False

    # Test non-bool values
    with pytest.raises(TypeError):
        data.single_value = 1  # type: ignore[assignment]  # test with a "truthy" value not being a bool
    assert buffer == expected_buffer  # buffer not updated

    with pytest.raises(TypeError):
        data.single_value = []  # type: ignore[assignment]  # test with a "falsy" value not being a bool
    assert buffer == expected_buffer  # buffer not updated

    data.single_value = True  # Reset to True for array tests
    expected_content = pack("<?", True)

    # Test bool array
    data.value_array = [True, False, True]
    expected_content += pack("<3?", True, False, True)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.value_array[0] is True
    assert data.value_array[1] is False
    assert data.value_array[2] is True

    with pytest.raises(ValueError):
        data.value_array = [True, False, True, False]  # Too many values
    assert buffer == expected_buffer  # buffer not updated
    data.value_array = [True, False, True]  # reset

    # Test bool matrix
    data.value_matrix = [
        [True, False],
        [False, True],
        [True, True],
    ]
    expected_content += pack("<6?", True, False, False, True, True, True)
    expected_buffer = expected_content + t.NULL * (buffer_size - len(expected_content))
    assert buffer == expected_buffer
    assert data.value_matrix[0] == [True, False]
    assert data.value_matrix[1] == [False, True]
    assert data.value_matrix[2] == [True, True]

    with pytest.raises(ValueError):
        data.value_matrix = [
            [True, False],
            [False, True],
        ]  # Not enough rows
    assert buffer == expected_buffer  # buffer not updated

    # Test that we can read the full buffer and verify all values
    new_data = BoolStruct(buffer)
    assert new_data.single_value is True
    assert list(new_data.value_array) == [True, False, True]
    assert new_data.value_matrix == [
        [True, False],
        [False, True],
        [True, True],
    ]
