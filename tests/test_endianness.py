import sys

import pytest

from databytes import BinaryStruct
from databytes import types as t
from databytes.types import Endianness


def test_endianness_values():
    assert str(Endianness.NATIVE) == "="
    assert str(Endianness.LITTLE) == "<"
    assert str(Endianness.BIG) == ">"
    assert str(Endianness.NETWORK) == "!"


def test_endianness_byte_order():
    assert Endianness.LITTLE.byte_order == Endianness.LITTLE
    assert Endianness.BIG.byte_order == Endianness.BIG
    assert Endianness.NATIVE.byte_order == Endianness.LITTLE if sys.byteorder == "little" else Endianness.BIG
    assert Endianness.NETWORK.byte_order == Endianness.BIG


def test_default_endianness(monkeypatch):
    # Ensure default is LITTLE when no environment variable is set
    monkeypatch.setenv("DATABYTES_ENDIANNESS", "")

    assert Endianness.get_default() == Endianness.NATIVE


def test_environment_variable_override(monkeypatch):
    monkeypatch.setenv("DATABYTES_ENDIANNESS", "LITTLE")
    assert Endianness.get_default() == Endianness.LITTLE

    monkeypatch.setenv("DATABYTES_ENDIANNESS", "BIG")
    assert Endianness.get_default() == Endianness.BIG

    monkeypatch.setenv("DATABYTES_ENDIANNESS", "NETWORK")
    assert Endianness.get_default() == Endianness.NETWORK

    monkeypatch.setenv("DATABYTES_ENDIANNESS", "NATIVE")
    assert Endianness.get_default() == Endianness.NATIVE


def test_invalid_endianness(monkeypatch):
    monkeypatch.setenv("DATABYTES_ENDIANNESS", "INVALID")
    with pytest.raises(ValueError):
        Endianness.get_default()

    # lowercase of valid bames is not ok
    monkeypatch.setenv("DATABYTES_ENDIANNESS", "big")
    with pytest.raises(ValueError):
        Endianness.get_default()

    # value of the enum are not ok
    monkeypatch.setenv("DATABYTES_ENDIANNESS", ">")
    with pytest.raises(ValueError):
        Endianness.get_default()


def test_setting_via_class_attribute():
    class LittleEndianStruct(BinaryStruct):
        _endianness = Endianness.LITTLE
        value: t.uint16

    class BigEndianStruct(BinaryStruct):
        _endianness = Endianness.BIG
        value: t.uint16

    class NetworkEndianStruct(BinaryStruct):
        _endianness = Endianness.NETWORK
        value: t.uint16

    class NativeEndianStruct(BinaryStruct):
        _endianness = Endianness.NATIVE
        value: t.uint16

    # Test that the byte order is actually respected
    buffer = bytearray(2)
    value = 0x1234  # will be stored as 34 12 in little endian, 12 34 in big endian

    # Little endian
    lstruct = LittleEndianStruct(buffer)
    assert lstruct._endianness == Endianness.LITTLE
    lstruct.value = value
    assert buffer == b"\x34\x12"

    # Big endian
    bstruct = BigEndianStruct(buffer)
    assert bstruct._endianness == Endianness.BIG
    bstruct.value = value
    assert buffer == b"\x12\x34"

    # Network (equivalent to big endian)
    wstruct = NetworkEndianStruct(buffer)
    assert wstruct._endianness == Endianness.NETWORK
    wstruct.value = value
    assert buffer == b"\x12\x34"

    # Native (depend on the system)
    nstruct = NativeEndianStruct(buffer)
    assert nstruct._endianness == Endianness.NATIVE
    nstruct.value = value
    if sys.byteorder == "little":
        assert buffer == b"\x34\x12"
    else:
        assert buffer == b"\x12\x34"


def test_setting_via_instance_attribute():
    class MyStruct(BinaryStruct):
        value: t.uint16

    # Test that the byte order is actually respected
    buffer = bytearray(2)
    value = 0x1234  # will be stored as 34 12 in little endian, 12 34 in big endian

    # Little endian
    lstruct = MyStruct(buffer, endianness=Endianness.LITTLE)
    assert lstruct._endianness == Endianness.LITTLE
    lstruct.value = value
    assert buffer == b"\x34\x12"

    # Big endian
    bstruct = MyStruct(buffer, endianness=Endianness.BIG)
    assert bstruct._endianness == Endianness.BIG
    bstruct.value = value
    assert buffer == b"\x12\x34"

    # Network (equivalent to big endian)
    wstruct = MyStruct(buffer, endianness=Endianness.NETWORK)
    assert wstruct._endianness == Endianness.NETWORK
    wstruct.value = value
    assert buffer == b"\x12\x34"

    # Native (depend on the system)
    nstruct = MyStruct(buffer, endianness=Endianness.NATIVE)
    assert nstruct._endianness == Endianness.NATIVE
    nstruct.value = value
    if sys.byteorder == "little":
        assert buffer == b"\x34\x12"
    else:
        assert buffer == b"\x12\x34"


def test_endianness_passing():
    class LittleEndianChildStruct(BinaryStruct):
        _endianness = Endianness.LITTLE
        value: t.uint16

    class BigEndianChildStruct(BinaryStruct):
        _endianness = Endianness.BIG
        value: t.uint16

    class BigEndianParentWithBigEndianChildStruct(BinaryStruct):
        _endianness = Endianness.BIG
        value: t.uint16
        child: BigEndianChildStruct

    class BigEndianParentWithLittleEndianChildStruct(BinaryStruct):
        _endianness = Endianness.BIG
        value: t.uint16
        child: LittleEndianChildStruct

    class LittleEndianParentWithBigEndianChildStruct(BinaryStruct):
        _endianness = Endianness.LITTLE
        value: t.uint16
        child: BigEndianChildStruct

    class LittleEndianParentWithLittleEndianChildStruct(BinaryStruct):
        _endianness = Endianness.LITTLE
        value: t.uint16
        child: LittleEndianChildStruct

    buffer = bytearray(4)
    value = 0x1234  # will be stored as 34 12 in little endian, 12 34 in big endian
    b_buffer = t.NULL * 2 + b"\x12\x34"
    l_buffer = t.NULL * 2 + b"\x34\x12"

    # passing class endianness to sub-struct
    bbstruct = BigEndianParentWithBigEndianChildStruct(buffer)
    assert bbstruct.child._endianness == Endianness.BIG
    bbstruct.child.value = value
    assert buffer == b_buffer

    blstruct = BigEndianParentWithLittleEndianChildStruct(buffer)
    assert blstruct.child._endianness == Endianness.BIG
    blstruct.child.value = value
    assert buffer == b_buffer

    lbstruct = LittleEndianParentWithBigEndianChildStruct(buffer)
    assert lbstruct.child._endianness == Endianness.LITTLE
    lbstruct.child.value = value
    assert buffer == l_buffer

    llstruct = LittleEndianParentWithLittleEndianChildStruct(buffer)
    assert llstruct.child._endianness == Endianness.LITTLE
    llstruct.child.value = value
    assert buffer == l_buffer

    class ParentWithBigEndianChildStruct(BinaryStruct):
        value: t.uint16
        child: BigEndianChildStruct

    class ParentWithLittleEndianChildStruct(BinaryStruct):
        value: t.uint16
        child: LittleEndianChildStruct

    # passing instance endianness to sub-struct
    bstruct = ParentWithBigEndianChildStruct(buffer, endianness=Endianness.BIG)
    assert bstruct.child._endianness == Endianness.BIG
    bstruct.child.value = value
    assert buffer == b_buffer

    bstruct = ParentWithBigEndianChildStruct(buffer, endianness=Endianness.LITTLE)
    assert bstruct.child._endianness == Endianness.LITTLE
    bstruct.child.value = value
    assert buffer == l_buffer

    lstruct = ParentWithLittleEndianChildStruct(buffer, endianness=Endianness.BIG)
    assert lstruct.child._endianness == Endianness.BIG
    lstruct.child.value = value
    assert buffer == b_buffer

    lstruct = ParentWithLittleEndianChildStruct(buffer, endianness=Endianness.LITTLE)
    assert lstruct.child._endianness == Endianness.LITTLE
    lstruct.child.value = value
    assert buffer == l_buffer
