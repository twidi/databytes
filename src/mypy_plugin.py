from functools import partial
from typing import Callable, Optional

from mypy.nodes import TypeInfo
from mypy.plugin import AnalyzeTypeContext, Plugin
from mypy.types import AnyType, RawExpressionType, TypeOfAny
from mypy.types import Type as MypyType

DBTYPES_TO_PYTHON = {
    # Explicit size integers
    "uint8": "builtins.int",
    "int8": "builtins.int",
    "uint16": "builtins.int",
    "int16": "builtins.int",
    "uint32": "builtins.int",
    "int32": "builtins.int",
    "uint64": "builtins.int",
    "int64": "builtins.int",
    # Alternative names
    "byte": "builtins.int",
    "ubyte": "builtins.int",
    "short": "builtins.int",
    "ushort": "builtins.int",
    # Floating point
    "float32": "builtins.float",
    "float64": "builtins.float",
    # Alternative names
    "float": "builtins.float",
    "double": "builtins.float",
    # Other
    "bool": "builtins.bool",
    "char": "builtins.bytes",  # used for single chars or arrays of chars
    "string": "builtins.str",  # used for single strings or arrays of strings
}


class BinaryStructPlugin(Plugin):
    def get_type_analyze_hook(self, fullname: str) -> Optional[Callable[[AnalyzeTypeContext], MypyType]]:
        if fullname.startswith("databytes.types."):
            db_type = fullname.split("databytes.types.")[1]
            return partial(db_type_hook, db_type=db_type) if db_type in DBTYPES_TO_PYTHON else None

        if not fullname.startswith("builtins."):
            try:
                real_type = self.lookup_fully_qualified(fullname)
            except Exception:
                pass
            else:
                if (
                    real_type
                    and isinstance(real_type.node, TypeInfo)
                    and real_type.node.mro
                    and any(parent_type.fullname == "databytes.BinaryStruct" for parent_type in real_type.node.mro[1:])
                ):
                    return partial(substruct_hook, fullname=fullname)

        return None


def check_dimensions(ctx: AnalyzeTypeContext) -> bool:
    for dimension in ctx.type.args:
        if (
            not isinstance(dimension, RawExpressionType)
            or not isinstance(dimension.literal_value, int)
            or dimension.literal_value <= 0
        ):
            ctx.api.fail(
                f"{ctx.type.name}[*dimensions]: dimensions should be literal positive integers.",
                ctx.context,
            )
            return False
    return True


def substruct_hook(ctx: AnalyzeTypeContext, fullname: str) -> MypyType:
    api = ctx.api
    if api is None:
        return AnyType(TypeOfAny.from_error)

    final_type = api.named_type(fullname)
    if ctx.type.args:
        if not check_dimensions(ctx):
            return AnyType(TypeOfAny.from_error)

        for _ in ctx.type.args:
            final_type = api.named_type("builtins.list", [final_type])

        return final_type

    return final_type


def db_type_hook(ctx: AnalyzeTypeContext, db_type: str) -> MypyType:
    api = ctx.api
    if api is None:
        return AnyType(TypeOfAny.from_error)

    python_type = api.named_type(DBTYPES_TO_PYTHON[db_type])

    if not ctx.type.args:
        return python_type

    if not check_dimensions(ctx):
        return AnyType(TypeOfAny.from_error)

    nb_dimensions = len(ctx.type.args)

    if db_type == "string":
        # strings are already a list of chars
        nb_dimensions -= 1

    for _ in range(nb_dimensions):
        python_type = api.named_type("builtins.list", [python_type])

    return python_type


def plugin(version: str) -> type[Plugin]:
    """Entry point for mypy."""
    return BinaryStructPlugin
