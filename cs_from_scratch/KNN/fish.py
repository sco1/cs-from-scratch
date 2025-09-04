import typing as t
from dataclasses import dataclass

from cs_from_scratch.KNN.knn import DataPoint


@dataclass
class Fish(DataPoint):
    kind: str
    weight: float
    length1: float
    length2: float
    length3: float
    height: float
    width: float

    @classmethod
    def from_string_data(cls, data: list[str]) -> t.Self:
        return cls(
            kind=data[0],
            weight=float(data[1]),
            length1=float(data[2]),
            length2=float(data[3]),
            length3=float(data[4]),
            height=float(data[5]),
            width=float(data[6]),
        )

    def distance(self, other: t.Self) -> float:
        return (
            (self.length1 - other.length1) ** 2
            + (self.length2 - other.length2) ** 2
            + (self.length3 - other.length3) ** 2
            + (self.height - other.height) ** 2
            + (self.width - other.width) ** 2
        ) ** 0.5
