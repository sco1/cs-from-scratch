from __future__ import annotations

import typing as t

COLOR_T: t.TypeAlias = tuple[int, int, int]


class Coord(t.NamedTuple):  # noqa: D101
    x: int
    y: int

    def shift(self, delta: int) -> Coord:
        """Return a new coordinate with its components both shifted by `delta`."""
        return Coord(x=self.x + delta, y=self.y + delta)

    def scale(self, factor: int | float) -> Coord:
        """
        Return a new coordinate with its components both multipled by `factor`.

        NOTE: Scaled components wil be cast to `int`, truncating any floating point component.
        """
        return Coord(x=int(self.x * factor), y=int(self.y * factor))


COORDS_T: t.TypeAlias = list[Coord]
