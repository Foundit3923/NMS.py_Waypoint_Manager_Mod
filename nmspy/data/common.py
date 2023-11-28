import ctypes
import types
from typing import Any, Union, TYPE_CHECKING

from nmspy.hashing import fnv_1a

if TYPE_CHECKING:
    from ctypes import _Pointer


class Colour(ctypes.Structure):
    _fields_ = [
        ("r", ctypes.c_float),
        ("g", ctypes.c_float),
        ("b", ctypes.c_float),
        ("a", ctypes.c_float)
    ]


class Vector2f(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
    ]


class Vector3f(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
    ]


class Vector4f(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
        ("w", ctypes.c_float),
    ]


class Vector4i(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_int32),
        ("y", ctypes.c_int32),
        ("z", ctypes.c_int32),
        ("w", ctypes.c_int32),
    ]


class GcSeed(ctypes.Structure):
    _fields_ = [
        ("Seed", ctypes.c_longlong),
        ("UseSeedValue", ctypes.c_ubyte),
    ]


class Quaternion(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
        ("w", ctypes.c_float),
    ]


class cTkDynamicArray(ctypes.Structure):
    _template_type = ctypes.c_char
    _fields_ = [
        ("mArray", ctypes.c_ulonglong),
        ("miSize", ctypes.c_uint32),
        ("mbAllocatedFromData", ctypes.c_ubyte),
        ("_macMagicPad", ctypes.c_char * 0x3)
    ]

    mArray: int
    miSize: int
    mbAllocatedFromData: bool

    @property
    def value(self) -> Any:
        from nmspy.memutils import map_struct

        if self.mArray == 0 or self.miSize == 0:
            # Empty lists are store with an empty pointer in mem.
            return []
        return map_struct(self.mArray, self._template_type * self.miSize)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.miSize})"

    def __class_getitem__(cls: type["cTkDynamicArray"], key: Union[tuple[Any], Any]):
        _cls: type["cTkDynamicArray"] = types.new_class(f"cTkDynamicArray<{key}>", (cls,))
        _cls._template_type = key
        return _cls

    def __len__(self) -> int:
        return self.miSize


class cTkDynamicString(ctypes.Structure):
    _fields_ = [
        ("mArray", ctypes.c_char_p),
        ("miSize", ctypes.c_uint32),
        ("mbAllocatedFromData", ctypes.c_ubyte),
        ("_macMagicPad", ctypes.c_char * 0x3)
    ]

    mArray: bytes
    miSize: int
    mbAllocatedFromData: bool

    @property
    def value(self) -> bytes:
        return self.mArray

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.miSize})"

    def __str__(self) -> str:
        return self.value.decode()

    def __len__(self) -> int:
        return self.miSize


class TkID(ctypes.Structure):
    _align_ = 0x10  # One day this will work...
    _size = 0x10  # This should only ever be 0x10 or 0x20...
    value: bytes

    def __class_getitem__(cls: type["TkID"], key: int):
        _cls: type["TkID"] = types.new_class(f"TkID<0x{key:X}>", (cls,))
        _cls._size = key
        _cls._fields_ = [
            ("value", ctypes.c_char * _cls._size)
        ]
        return _cls

    def __str__(self) -> str:
        return self.value.decode()

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return fnv_1a(str(self), self._size)


class cTkFixedString(ctypes.Structure):
    _size = 0x10
    value: bytes

    def __class_getitem__(cls: type["cTkFixedString"], key: int):
        _cls: type["cTkFixedString"] = types.new_class(f"cTkFixedString<0x{key:X}>", (cls,))
        _cls._size = key
        _cls._fields_ = [
            ("value", ctypes.c_char * _cls._size)
        ]
        return _cls

    def __str__(self) -> str:
        return self.value.decode()

    def __repr__(self) -> str:
        return str(self)


class std__vector(ctypes.Structure):
    _template_type = ctypes.c_char
    if TYPE_CHECKING:
        _first: _Pointer[Any]
        _last: _Pointer[Any]
        _end: _Pointer[Any]

    def __class_getitem__(cls: type["std__vector"], key: int):
        _cls: type["cTkFixedString"] = types.new_class(f"std::vector<{key}>", (cls,))
        _cls._template_type = key
        _cls._fields_ = [
            ("_first", ctypes.POINTER(_cls._template_type)),
            ("_last", ctypes.POINTER(_cls._template_type)),
            ("_end", ctypes.POINTER(_cls._template_type)),
        ]
        return _cls

    def __len__(self) -> int:
        return (
            ctypes.addressof(self._last.contents) -
            ctypes.addressof(self._first.contents)
        ) // 0x8  # Assuming 64 bit architecture

    def __getitem__(self, i: int):
        return self._first[i]

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def clear(self):
        nullptr = ctypes.POINTER(self._template_type)
        self._first = nullptr()
        self._last = nullptr()
        self._end = nullptr()
