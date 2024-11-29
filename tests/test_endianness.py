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


def test_byte_order():
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


def test_endianness_coherence():
    class LittleEndianChildStruct(BinaryStruct):
        _endianness = Endianness.LITTLE
        value: t.uint16

    class BigEndianChildStruct(BinaryStruct):
        _endianness = Endianness.BIG
        value: t.uint16

    class BigEndianParentStruct(BinaryStruct):
        _endianness = Endianness.BIG
        value: t.uint16
        child: BigEndianChildStruct

    with pytest.raises(ValueError, match="Sub-struct LittleEndianChildStruct must have same endianness as parent: BIG"):

        class LittleEndianParentStruct(BinaryStruct):
            _endianness = Endianness.BIG
            value: t.uint16
            child: LittleEndianChildStruct
