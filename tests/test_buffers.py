import array
import ctypes
import io
import mmap
import pickle
import tempfile
from multiprocessing.shared_memory import SharedMemory

import pytest

from databytes import BinaryStruct
from databytes import types as t


class MainStruct(BinaryStruct):
    value: t.uint8
    text: t.string[5]


def test_bytes_buffer() -> None:
    # Test using bytes
    buffer = b"\x01" + b"Hello"

    struct = MainStruct(buffer)
    assert struct.value == 1
    assert struct.text == "Hello"

    # Test writing to bytes - should fail as bytes are immutable
    with pytest.raises(TypeError):
        struct.value = 2


def test_bytearray_buffer() -> None:
    # Test using bytearray
    buffer = bytearray(b"\x01" + b"Hello")

    struct = MainStruct(buffer)
    assert struct.value == 1
    assert struct.text == "Hello"

    # Test writing to bytearray
    struct.value = 2
    struct.text = "World"
    assert buffer == b"\x02" + b"World"


def test_immutable_memoryview_buffer() -> None:
    # Test using immutable memoryview
    buffer = memoryview(b"\x01" + b"Hello")

    struct = MainStruct(buffer)
    assert struct.value == 1
    assert struct.text == "Hello"

    # Test writing to memoryview of bytes - should fail as underlying buffer is immutable
    with pytest.raises(TypeError):
        struct.value = 2


def test_mutable_memoryview_buffer() -> None:
    # Test using mutable memoryview
    buffer = memoryview(bytearray(b"\x01" + b"Hello"))

    struct = MainStruct(buffer)
    assert struct.value == 1
    assert struct.text == "Hello"

    # Test writing to memoryview of byterray - should succeed as underlying buffer is mutable
    struct.value = 2
    struct.text = "World"
    assert buffer == b"\x02" + b"World"


def test_shared_memory_buffer() -> None:
    """Test using shared memory buffer."""
    shm = SharedMemory(create=True, size=MainStruct._nb_bytes, name="test_buffer")
    buffer = shm.buf
    buffer[:] = b"\x01" + b"Hello"

    # Get another access to the shared memory
    shm2 = SharedMemory(name="test_buffer")
    buffer2 = shm2.buf
    assert buffer2 == b"\x01" + b"Hello"

    struct: MainStruct | None = None
    try:
        struct = MainStruct(buffer)
        assert struct.value == 1
        assert struct.text == "Hello"

        struct.value = 2
        struct.text = "World"
        assert buffer == b"\x02" + b"World"

        assert buffer2 == b"\x02" + b"World"

    finally:
        if struct is not None:
            struct.free_buffer()
        shm2.close()
        shm.close()
        shm.unlink()


def test_array_buffer() -> None:
    # Test using array.array - another common buffer type

    buffer = array.array("B", b"\x01" + b"Hello")

    struct = MainStruct(buffer)
    assert struct.value == 1
    assert struct.text == "Hello"

    # Test writing to array
    struct.value = 2
    struct.text = "World"
    assert bytes(buffer) == b"\x02" + b"World"


def test_bytesio_buffer() -> None:
    # Test using io.BytesIO
    buffer = io.BytesIO(b"\x01" + b"Hello")
    buffer_view = buffer.getbuffer()

    struct = MainStruct(buffer_view)
    assert struct.value == 1
    assert struct.text == "Hello"

    # Test writing to BytesIO buffer
    struct.value = 2
    struct.text = "World"
    assert bytes(buffer_view) == b"\x02" + b"World"
    assert buffer.getvalue() == b"\x02" + b"World"


def test_invalid_list_buffer() -> None:
    # Test using list
    buffer = list(b"\x01" + b"Hello")

    struct = MainStruct(buffer)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        struct.value = 1


def test_too_small_buffer() -> None:
    # Test using buffer that's too small
    with pytest.raises(ValueError):
        MainStruct(b"\x01")


def test_numpy_buffer() -> None:
    try:
        import numpy as np
    except ImportError:
        pytest.skip("numpy is not installed")

    # Test using numpy array
    buffer = np.frombuffer(b"\x01" + b"Hello", dtype=np.uint8)
    buffer_copy = buffer.copy()  # make it writable

    struct = MainStruct(buffer_copy)
    assert struct.value == 1
    assert struct.text == "Hello"

    # Test writing to numpy array
    struct.value = 2
    struct.text = "World"
    assert buffer_copy.tobytes() == b"\x02" + b"World"

    # Test with non-writable array
    struct_readonly = MainStruct(buffer)  # original buffer is read-only
    with pytest.raises(TypeError):
        struct_readonly.value = 3


def test_mmap_buffer() -> None:
    # Test using memory-mapped file
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"\x01" + b"Hello")
        f.flush()

        with mmap.mmap(f.fileno(), 0) as mm:
            struct = MainStruct(mm)
            assert struct.value == 1
            assert struct.text == "Hello"

            # Test writing to mmap
            struct.value = 2
            struct.text = "World"
            assert mm[:6] == b"\x02" + b"World"


def test_ctypes_buffer() -> None:
    # Test using ctypes array
    buffer = (ctypes.c_uint8 * MainStruct._nb_bytes)()

    # Initialize buffer
    for i, b in enumerate(b"\x01" + b"Hello"):
        buffer[i] = b

    struct = MainStruct(buffer)
    assert struct.value == 1
    assert struct.text == "Hello"

    # Test writing to ctypes array
    struct.value = 2
    struct.text = "World"
    assert bytes(buffer) == b"\x02" + b"World"


def test_invalid_pickle_buffer() -> None:
    if not hasattr(pickle, "PickleBuffer"):
        pytest.skip("PickleBuffer not available (Python < 3.8)")

    # Create initial data
    buffer = pickle.PickleBuffer(bytearray(b"\x01" + b"Hello"))

    with pytest.raises(TypeError, match="has no len"):
        MainStruct(buffer)  # type: ignore[arg-type]


def test_invalid_file_buffer() -> None:
    # Test that regular file objects don't work as buffers (use mmap for instead)
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"\x01" + b"Hello")
        f.flush()
        f.seek(0)

        # Binary file mode
        with pytest.raises(TypeError):
            MainStruct(f)  # type: ignore[arg-type]

        # Reading the content is possible, though
        content = f.read()
        struct = MainStruct(content)
        assert struct.value == 1
        with pytest.raises(TypeError):
            struct.value = 2


def test_freeing_buffer() -> None:
    # Test freeing buffer with propagation

    class ChildStruct(BinaryStruct):
        value: t.uint8

    class ParentStruct(BinaryStruct):
        children: ChildStruct[2]

    class GrandParentStruct(BinaryStruct):
        child: ParentStruct

    buffer = bytearray(GrandParentStruct._nb_bytes)
    struct = GrandParentStruct(buffer)
    struct.child.children[0].value = 1
    struct.child.children[1].value = 2

    struct.free_buffer()
    assert struct._buffer is None
    assert struct.child._buffer is None  # type: ignore[unreachable]  # because it cannot be None "in theory"
    assert struct.child.children[0]._buffer is None
    assert struct.child.children[1]._buffer is None


def test_buffer_offset() -> None:
    # Test settings a buffer with an offset, and attaching another one

    class ChildStruct(BinaryStruct):
        value: t.uint8

    class ParentStruct(BinaryStruct):
        children: ChildStruct[2]

    class GrandParentStruct(BinaryStruct):
        value: t.uint8
        child: ParentStruct

    buffer = bytearray(20)
    struct = GrandParentStruct(buffer, 10)
    struct.value = 1
    struct.child.children[0].value = 2
    struct.child.children[1].value = 3

    assert struct._nb_bytes == 3
    assert buffer == t.NULL * 10 + b"\x01\x02\x03" + t.NULL * 7

    buffer2 = t.NULL * 5 + b"\x04\x05\x06" + t.NULL * 2

    struct.attach_buffer(buffer2, 5)
    assert struct.value == 4
    assert struct.child.children[0].value == 5
    assert struct.child.children[1].value == 6


def test_clearing_buffer() -> None:
    # Test clearing buffer

    class ChildStruct(BinaryStruct):
        value: t.char

    class ParentStruct(BinaryStruct):
        children: ChildStruct[2]

    class GrandParentStruct(BinaryStruct):
        value: t.char
        child: ParentStruct

    buffer = bytearray(b"a" * 50)
    struct = GrandParentStruct(buffer, offset=10)
    assert struct.value == b"a"
    assert struct.child.children[0].value == b"a"
    assert struct.child.children[1].value == b"a"

    struct.clear_buffer()

    # our values should be NULL
    assert struct.value == t.NULL
    assert struct.child.children[0].value == t.NULL
    assert struct.child.children[1].value == t.NULL

    # buffer outside of our offset + size should be unchanged

    assert buffer == b"a" * 10 + t.NULL * 3 + b"a" * 37
