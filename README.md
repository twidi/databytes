# DataBytes

A Python library providing a class-based approach to serialize and deserialize binary data, built on top of Python's `struct` module. DataBytes makes it easy to work with binary structures, shared memory, and memory-mapped files in a type-safe and object-oriented way.

## Features

- Class-based binary structure definitions
- Type-safe field declarations
- Support for nested structures and arrays
- Use standard python binary packing and unpacking via the `struct` package
- Support for Python 3.10+

## Installation

```bash
pip install databytes
```

## Quick Start

```python
from databytes import BinaryStruct
from databytes import types as t

class Point(BinaryStruct):
    name: t.string[12]  # fixed-length string of 12 chars
    x: t.uint16
    y: t.uint16

class Rectangle(BinaryStruct):
    top_left: Point
    bottom_right: Point
    area: t.uint32
    selected_points: Point[2]   # array of 2 points

# Create a new structure with a buffer
assert Rectangle._nb_bytes == 68  # (12+4) for each point + 4 for area

# can be a bytes (read-only), bytearray, memoryview (like the `.buf` of a shared memory), mmap.mmap, array.array, ctypes.Array, numpy bytes array
buffer = bytearray(Rectangle._nb_bytes)

rect = Rectangle(buffer)

# Set values
rect.top_left.name = "Top Left"
rect.top_left.x = 0
rect.top_left.y = 0
rect.bottom_right.name = "Bottom Right"
rect.bottom_right.x = 10
rect.bottom_right.y = 10
rect.area = 100
rect.selected_points[0].name = "Selected 1"
rect.selected_points[0].x = 1
rect.selected_points[0].y = 2
rect.selected_points[1].name = "Selected 2"
rect.selected_points[1].x = 3
rect.selected_points[1].y = 4

# buffer is updated
print(buffer)
# bytearray(b'Top Left\x00\x00\x00\x00\x00\x00\x00\x00Bottom Right\n\x00\n\x00d\x00\x00\x00Selected 1\x00\x00\x01\x00\x02\x00Selected 2\x00\x00\x03\x00\x04\x00')

# Load this buffer into another Rectangle instance
rect2 = Rectangle(buffer)
assert rect2.top_left.name == "Top Left"
assert rect2.top_left.x == 0
assert rect2.top_left.y == 0
assert rect2.bottom_right.name == "Bottom Right"
assert rect2.bottom_right.x == 10
assert rect2.bottom_right.y == 10
assert rect2.area == 100
assert rect2.selected_points[0].name == "Selected 1"
assert rect2.selected_points[0].x == 1
assert rect2.selected_points[0].y == 2
assert rect2.selected_points[1].name == "Selected 2"
assert rect2.selected_points[1].x == 3
assert rect2.selected_points[1].y == 4

```


## Key Concepts

- **Binary Structures**: Define your data structures using Python classes that inherit from `BinaryStruct`
- **Typing**: Field are declared using type hints
- **Memory Efficiency**: Direct memory access without unnecessary copies
- **Shared Memory**: Easy integration with multiprocessing using shared memory buffers
- **Extensibility**: Create custom field types by extending the base types

## Dependencies

- Python >= 3.10
- typing-extensions
- numpy  (only used to create the `Buffer` type alias 😑 )

Optional dependencies:
- rich (for enhanced display capabilities)

## Available types

### Basic Types

As some types have the same name as builtins, the best way to import them is to use `from databytes import types as t` and use the `t.` prefix:

```python
from databytes import BinaryStruct
from databytes import types as t

class Data(BinaryStruct):
    field: t.uint16
```

- `uint8` / `ubyte` (1 byte, coalesce to python int)
- `int8` / `byte` (1 byte, coalesce to python int)
- `uint16` / `ushort` (2 bytes, coalesce to python int)
- `int16` / `short` (2 bytes, coalesce to python int)
- `uint32` (4 bytes, coalesce to python int)
- `int32` (4 bytes, coalesce to python int)
- `uint64` (8 bytes, coalesce to python int)
- `int64` (8 bytes, coalesce to python int)
- `float32` / `float` (4 bytes, coalesce to python float)
- `float64` / `double` (8 bytes, coalesce to python float)
- `char`  (1 byte, coalesce to python bytes)
- `string` (fixed-length string, automatically padded with nulls, coalesce to python str)

### Custom Types

You can use as a field another struct:

```python
from databytes import BinaryStruct
from databytes import types as t

class Point(BinaryStruct):
    x: t.uint16
    y: t.uint16

class Rectangle(BinaryStruct):
    top_left: Point
    bottom_right: Point

buffer = bytearray(Rectangle._nb_bytes)
rect = Rectangle(buffer)
rect.top_left.x = 0
rect.top_left.y = 0
rect.bottom_right.x = 10
rect.bottom_right.y = 10
```

*WARNING*: It's actually not possible to set the values of a sub-struct directly without using the attributes. It's due to the fact that the sub-structs instances are tied to their parent buffer, with the correct offset.

```python
point_buffer  = bytearray(Point._nb_bytes)
point = Point(point_buffer)
point.x = 5
point.y = 5
rect.bottom_right = point

# when reading the buffer on another instance, we'll have the original values
rect2 = Rectangle(buffer)
assert rect2.bottom_right.x == 10
assert rect2.bottom_right.y == 10
```

### Arrays

Basic and custom types can be used in arrays of any dimension:

```python
from databytes import BinaryStruct
from databytes import types as t

class Point(BinaryStruct):
    x: t.uint16
    y: t.uint16

class Rectangle(BinaryStruct):
    corners: Point[2]  # array of 2 points
    matrix_2dim: Point[2, 3]  # matrix of 2x2 points
    matrix_3dim: Point[2, 3, 4]  # matrix of 2x2x2 points
    
```

*WARNING*: The dimensions are defined in reverse order: `Point[2, 3, 4]` is a list of 4 lists of 3 lists of 2 points

*WARNING*: It's actually not possible to set the arrays instances directly without using the concrete slicing and attributes. It's due to the fact that the sub-structs instances are tied to their parent buffer, with the correct offset.

```python
class Point(BinaryStruct):
    x: t.uint16
    y: t.uint16

class Rectangle(BinaryStruct):
    corners: Point[2]  # array of 2 points

point1_buffer  = bytearray(Point._nb_bytes)
point2_buffer  = bytearray(Point._nb_bytes)
point1 = Point(point1_buffer)
point1.x = 5
point1.y = 5
point2 = Point(point2_buffer)
point2.x = 10
point2.y = 10

buffer = bytearray(Rectangle._nb_bytes)
rect = Rectangle(buffer)
# Won't work
rect.corners[0] = point1
rect.corners[1] = point2
# Won't work either
rect.corners = [point1, point2]
# Will work
rect.corners[0].x = 5  # you can use `= point1.x`
rect.corners[0].y = 5
rect.corners[1].x = 10
rect.corners[1].y = 10
```

#### Special case for strings.

By default a string is a string of 1 character. To defined the max length, define the length as the first dimension:

```python
from databytes import BinaryStruct
from databytes import types as t

class Person(BinaryStruct):
    name: t.string[10]  # fixed-length string of 10 chars
```

When retrieving the value, you'll have a real string, not a list of characters. If the string is shorter than the allocated space, it will be null-padded in the buffer but retrieved as a real string without the nulls.

To define an array of strings, add more dimensions:

```python
from databytes import BinaryStruct
from databytes import types as t

class Person(BinaryStruct):
    name: t.string[10]  # fixed-length string of 10 chars
    aliases: t.string[10, 2]  # array of 2 strings of 10 chars
```

## API

### Key points

- `BinaryStruct` is the base class for all structures (`from databytes import BinaryStruct`)
- `types` module contains all available types (`from databytes import types as t`)
- a `BinaryStruct` instance is created taking a buffer as argument (`buffer = bytearray(Rectangle._nb_bytes); rect = Rectangle(buffer)`) and an optional offset for the start of the buffer to use

```python
from databytes import BinaryStruct
from databytes import types as t

class Data(BinaryStruct):
    field: t.uint16

buffer = bytearray(1000)

# here the data will be read/written at offset 100 of the buffer (and will only use the bytes size defined by the fields, here 2 bytes)
data = Data(buffer, 100)
```

### Supported buffers

We defined the `Buffer` type alias like this:

```python
Buffer: TypeAlias = bytes | bytearray | memoryview | mmap.mmap | array.array | ctypes.Array | np.ndarray
```

Not that all buffers are not writeable (like `bytes`, immutable `memoryview`s, immutable numpy arrays).

If you have another buffer type that we should support, please tell us.

You can use any buffer as long as:
- it works with `pack_info` and `unpack_from` from the python `struct` module
- it has a `__len__` method (we use it to ensure at init time that the buffer is big enough)

(of course, if it's not in our `Buffer` type alias, mypy won't be happy and you'll have to handle it)

### BinaryStruct extra fields

To not pollute the namespace, extra fields are prefixed with `_`:

- `_nb_bytes` (class var): number of bytes used by the structure (including sub-structs)
- `_struct_format` (class var): the format, using the python `struct` module format, of the whole structure (just for information)
- `_buffer` (instance var): the buffer used by the structure (the buffer passed to the constructor, will be the same for the main struct and all sub-structs)
- `_offset` (instance var): the offset of this specific structure in the buffer

You can define your own fields for your own purpose, as only the fields defined in `BinaryStruct` using the `types` module or sub structs inheriting from `BinaryStruct` are handled by the library:

```python
from databytes import BinaryStruct
from databytes import types as t

class Data(BinaryStruct):
    field: t.uint16
    my_field: str  # will not be handled by the library

    def __init__(self, my_field: str, buffer: Buffer, offset: int = 0) -> None:
        super().__init__(buffer, offset)
        self.my_field = my_field
```

### Pointing to another buffer

It's possible to use the same structure on different buffers:

```python
from databytes import BinaryStruct
from databytes import types as t

class Data(BinaryStruct):
    field: t.uint16

buffer1 = bytearray(1000)
buffer2 = bytearray(1000)

# will read/write the data at offset 100 of the buffer1
data = Data(buffer1, 100)

# will now read/write the data at offset 100 of the buffer2 (it's not possible to change the offset for now)
data.set_new_buffer(buffer2)
```

### Freeing the buffer

When using shared memory for example, the buffer must be freed before freeing the shared memory. To do that, use the `free_buffer` method:

```python
from databytes import BinaryStruct
from databytes import types as t

class Data(BinaryStruct):
    field: t.uint16

shm = SharedMemory(create=True, size=1000)
buffer = shm.buf

data: Data | None = None
try:
    data = Data(buffer)
    data.value = 2
    data.text = "World"

    # ...

finally:
    if data is not None:
        data.free_buffer()
    shm.close()
    shm.unlink()
``` 

Of course, here `data` cannot be used anymore unless you call `set_new_buffer` on it with another buffer.

### Utils

#### Layout information

You can get the layout of a structure with the `get_layout_info` function from `databytes.utils`:

```python
from databytes import BinaryStruct
from databytes import types as t
from databytes.utils import get_layout_info

class Point(BinaryStruct):
    x: t.uint16
    y: t.uint16

class Rectangle(BinaryStruct):
    corners: Point[2]  # array of 2 points

get_layout_info(Rectangle)
```

Will give you:

```python
StructLayoutInfo(
    name='Rectangle', 
    struct_class=<class '__main__.Rectangle'>, 
    struct_format='HHHH', 
    nb_bytes=8, 
    offset=0, 
    fields={
        'corners': FieldLayoutInfo(
            name='corners', 
            offset=0, 
            nb_bytes=8, 
            struct_format='HHHH', 
            nb_items=2, 
            dimensions=(2,), 
            python_type=<class '__main__.Point'>, 
            python_full_type=list[__main__.Point], 
            is_sub_struct=True, 
            sub_struct=None
        )
    }
)
```

Call it with `include_sub_structs_details=True` to get more details about the sub-structs, in the `sub_struct` field (recursively)
```python
StructLayoutInfo(
    name='Rectangle', 
    struct_class=<class '__main__.Rectangle'>
    struct_format='HHHH'
    nb_bytes=8
    offset=0
    fields={
        'corners': FieldLayoutInfo(
            name='corners'
            offset=0
            nb_bytes=8
            struct_format='HHHH'
            nb_items=2
            dimensions=(2,)
            python_type=<class '__main__.Point'>
            python_full_type=list[__main__.Point], 
            is_sub_struct=True, 
            sub_struct=StructLayoutInfo(
                name='Point', 
                struct_class=<class '__main__.Point'>, 
                struct_format='HH'
                nb_bytes=4
                offset=0
                fields={
                    'x': FieldLayoutInfo(
                        name='x'
                        offset=0
                        nb_bytes=2
                        struct_format='H',
                        nb_items=1,
                        dimensions=None,
                        python_type=<class 'int'>,
                        python_full_type=<class 'int'>,
                        is_sub_struct=False,
                        sub_struct=None
                    ),
                    'y': FieldLayoutInfo(
                        name='y', 
                        offset=2, 
                        nb_bytes=2, 
                        struct_format='H', 
                        nb_items=1, 
                        dimensions=None, 
                        python_type=<class 'int'>, 
                        python_full_type=<class 'int'>, 
                        is_sub_struct=False, 
                        sub_struct=None
                    )
                }
            )
        )
    }
)
```

#### Rich tables

You can get a `rich` (https://rich.readthedocs.io/en/latest) table representation of a structure with the `print_rich_table` function from `databytes.utils`:

Taking the previous example strucs:

```python
from databytes.utils import print_rich_table

print_rich_table(Rectangle)
```

Will give you:
```bash
                  Layout of Rectangle (8 bytes)                   
┏━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name    ┃ Offset ┃ Nb bytes ┃ Format ┃ Dimensions ┃ Python Type ┃
┡━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ corners │      0 │        8 │ HHHH   │       (2,) │ list[Point] │
└─────────┴────────┴──────────┴────────┴────────────┴─────────────┘
```

calling it with `include_sub_structs_details=True` will give you more details about the sub-structs:
```bash
                   Layout of Rectangle (8 bytes)                   
┏━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name    ┃ Offset ┃ Nb bytes ┃ Format ┃ Dimensions ┃ Python Type ┃
┡━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ corners │      0 │        8 │ HHHH   │       (2,) │ list[Point] │
└─────────┴────────┴──────────┴────────┴────────────┴─────────────┘
                   Layout of Point (4 bytes)                    
┏━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name ┃ Offset ┃ Nb bytes ┃ Format ┃ Dimensions ┃ Python Type ┃
┡━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ x    │      0 │        2 │ H      │       None │ int         │
│ y    │      2 │        2 │ H      │       None │ int         │
└──────┴────────┴──────────┴────────┴────────────┴─────────────┘
```

Instead of `print_riche_table` you can use `get_rich_table_string` so you can print it the way you want. Or `get_rich_table` to integrate the result in another rich component.

You can install the `rich` library independantly or by installing databytes with the `[extra]` dependency (`pip install databytes[extra]`).


## Mypy

We have our own `mypy` plugin so that `mypy` understands that `field: t.uint16` will resolve to an `int`, or `field: t.uint16[2]` will resolve to a `list[int]`.

It will also ensure that the dimensions (in `[]`) are literal positive integers.

To use the plugin, in your mypy configuration add `databytes.mypy_plugin` to your list of plugins.


## Development

To set up the development environment, first create a virtual environment using the method of your choice, activate it and, in it:

```bash
# Install development dependencies
make dev

# Prettify code
make format  # or `make pretty`

# Run linting tools (ruff and mypy)
make lint

# Run tests
make tests

# Run lint + tests
make checks
```

## License

MIT License - See the LICENSE file for details.

## Author

Stephane "Twidi" Angel (s.angel@twidi.com)

## Links

- Source: https://github.com/twidi/databytes
- Author's website: https://twidi.com