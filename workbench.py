#!/usr/bin/env python

import struct
from multiprocessing.shared_memory import SharedMemory

from databytes import BinaryStruct
from databytes import types as t


class MyStruct(BinaryStruct):
    uint16: t.uint16
    strings: t.string[10, 2]
    chars: t.char[5, 2]
    float64: t.double
    uint16s: t.uint16[3, 2, 2]


def print_struct_values(struct: MyStruct) -> None:
    """Helper to print values from a struct instance"""
    uint16: int = struct.uint16
    strings: list[str] = struct.strings
    chars: list[list[str]] = struct.chars
    float64: float = struct.float64
    uint16s: list[list[list[int]]] = struct.uint16s

    print("\nValues:")
    print(f"uint16: {uint16}")
    print(f"strings: {strings}")
    print(f"chars: {chars}")
    print(f"float64: {float64}")
    print(f"uint16s: {uint16s}")


if __name__ == "__main__":
    # Print the structure layout
    MyStruct.print_layout()

    # Create sample data
    test_data = (
        struct.pack("<H", 12345)  # uint16
        + b"Hello\x00\x00\x00\x00\x00"  # string[10]
        + b"World\x00\x00\x00\x00\x00"  # string[10]
        + b"Hello"  # chars[5]
        + b"World"  # chars[5]
        + struct.pack("<d", 3.14159)  # float64
        + struct.pack("<3H", 1, 2, 3)  # uint16s[3], element 0
        + struct.pack("<3H", 4, 5, 6)  # uint16s[3], element 1
        + struct.pack("<3H", 7, 8, 9)  # uint16s[3], element 2
        + struct.pack("<3H", 10, 11, 12)  # uint16s[3], element 3
    )

    # Test with shared memory
    shm = SharedMemory(create=True, size=MyStruct._nb_bytes)
    try:
        shm.buf[:] = test_data
        data = MyStruct(shm.buf)
        print_struct_values(data)
    finally:
        shm.close()
        shm.unlink()

    # Test with bytearray
    buffer = bytearray(test_data)
    data = MyStruct(buffer)
    print_struct_values(data)

    # Test with bytes
    data = MyStruct(test_data)
    print_struct_values(data)
