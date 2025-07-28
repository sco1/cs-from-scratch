import typing as t
from collections import abc

COLOR_T: t.TypeAlias = tuple[int, int, int]


class Coord(t.NamedTuple):  # noqa: D101
    x: int
    y: int


COORDS_T: t.TypeAlias = abc.Iterable[Coord]
