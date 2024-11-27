#!/usr/bin/env python

import gc
import struct
from contextlib import contextmanager
from multiprocessing.shared_memory import SharedMemory

from databytes import BinaryStruct
from databytes import types as t


class MySubSubStruct(BinaryStruct):
    simple: t.uint8


class MySubStruct(BinaryStruct):
    foo: t.string[5]  # a string of 5 chars max
    bar: t.uint16
    qux: t.string[5, 2]  # a list of 2 strings of 5 chars max
    sub: MySubSubStruct  # a sub-struct
    subs: MySubSubStruct[2, 2]  # a 2x2 list of sub-structs


class MyStruct(BinaryStruct):
    uint16: t.uint16
    strings: t.string[10, 2]  # a list of 2 strings of 10 chars max
    chars: t.char[5, 2]  # a list of 2 lists of 5 chars
    float64: t.double
    uint16s: t.uint16[3, 2, 2]  # a list of 2 lists of 2 lists of 3 uint16
    child: MySubStruct  # a sub-struct
    children: MySubStruct[2]  # a list of 2 sub-structs


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

    child: MySubStruct = struct.child

    foo: str
    bar: int
    qux: list[str]
    simple: int
    sub: MySubSubStruct
    subs_row: list[MySubSubStruct]
    subs: list[list[MySubSubStruct]]

    foo = child.foo
    bar = child.bar
    qux = child.qux

    print("child:")
    print(f"child.foo: {foo}")
    print(f"child.bar: {bar}")
    print(f"child.qux: {qux}")

    sub = child.sub
    subs = child.subs

    simple = child.sub.simple
    print(f"child.sub.simple: {simple}")

    for j, subs_row in enumerate(subs):
        for k, sub in enumerate(subs_row):
            simple = sub.simple
            print(f"child.subs[{j}][{k}].simple: {simple}")

    children: list[MySubStruct] = struct.children
    print("children:")

    for i, child in enumerate(children):
        foo = child.foo
        bar = child.bar
        qux = child.qux
        print(f"  {i}.foo: {child.foo}")
        print(f"  {i}.bar: {child.bar}")
        print(f"  {i}.qux: {child.qux}")

        sub = child.sub
        subs = child.subs

        simple = child.sub.simple
        print(f"  {i}.sub.simple: {simple}")

        for j, subs_row in enumerate(subs):
            for k, sub in enumerate(subs_row):
                simple = sub.simple
                print(f"  {i}.subs[{j}][{k}].simple: {simple}")


def test_shared_memory(test_data: bytes) -> None:
    shm = SharedMemory(create=True, size=MyStruct._nb_bytes)
    data: MyStruct | None = None
    try:
        shm.buf[:] = test_data
        data = MyStruct(shm.buf)
        print_struct_values(data)
    finally:
        if data is not None:
            data.free_buffer()
        shm.close()
        shm.unlink()


def test_bytearray(test_data: bytes) -> None:
    buffer = bytearray(test_data)
    data = MyStruct(buffer)
    print_struct_values(data)


def test_bytes(test_data: bytes) -> None:
    data = MyStruct(test_data)
    print_struct_values(data)


if __name__ == "__main__":
    # Print the structure layout
    MyStruct.print_layout()
    MySubStruct.print_layout()
    MySubSubStruct.print_layout()

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
        #
        # child: MySubStruct
        + b"Child"  # foo: string[5]
        + struct.pack("<H", 42)  # bar: uint16
        + b"qux00"  # qux[0]: string[5]
        + b"qux01"  # qux[1]: string[5]
        + struct.pack("<B", 1)  # sub.simple: MySubSubStruct
        + struct.pack("<B", 2)  # subs[0][0].simple: MySubSubStruct
        + struct.pack("<B", 3)  # subs[0][1].simple: MySubSubStruct
        + struct.pack("<B", 4)  # subs[1][0].simple: MySubSubStruct
        + struct.pack("<B", 5)  # subs[1][1].simple: MySubSubStruct
        #
        # children: MySubStruct * 2
        #
        # children[0]: MySubStruct
        + b"Kid 1"  # children[0].foo: string[5]
        + struct.pack("<H", 101)  # children[0].bar: uint16
        + b"qux10"  # children[0].qux[0]: string[5]
        + b"qux11"  # children[0].qux[1]: string[5]
        + struct.pack("<B", 6)  # children[0].sub.simple: MySubSubStruct
        + struct.pack("<B", 7)  # children[0].subs[0][0].simple: MySubSubStruct
        + struct.pack("<B", 8)  # children[0].subs[0][1].simple: MySubSubStruct
        + struct.pack("<B", 9)  # children[0].subs[1][0].simple: MySubSubStruct
        + struct.pack("<B", 10)  # children[0].subs[1][1].simple: MySubSubStruct
        #
        # children[1]: MySubStruct
        #
        + b"Kid 2"  # children[1].foo: string[5]
        + struct.pack("<H", 102)  # children[1].bar: uint16
        + b"qux20"  # children[1].qux[0]: string[5]
        + b"qux21"  # children[1].qux[1]: string[5]
        + struct.pack("<B", 11)  # children[1].sub.simple: MySubSubStruct
        + struct.pack("<B", 12)  # children[1].subs[0][0].simple: MySubSubStruct
        + struct.pack("<B", 13)  # children[1].subs[0][1].simple: MySubSubStruct
        + struct.pack("<B", 14)  # children[1].subs[1][0].simple: MySubSubStruct
        + struct.pack("<B", 15)  # children[1].subs[1][1].simple: MySubSubStruct
    )

    test_shared_memory(test_data)
    test_bytearray(test_data)
    test_bytes(test_data)
