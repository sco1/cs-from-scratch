import typing as t
from dataclasses import dataclass

import numpy as np

from cs_from_scratch.KNN.knn import DataPoint


@dataclass
class Digit(DataPoint):
    kind: str
    pixels: np.ndarray

    @classmethod
    def from_string_data(cls, data: list[str]) -> t.Self:
        return cls(kind=data[64], pixels=np.array(data[:64], dtype=np.uint32))

    def distance(self, other: t.Self) -> float:
        tmp = self.pixels - other.pixels
        return np.sqrt(np.dot(tmp.T, tmp))
