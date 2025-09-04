import csv
import typing as t
from collections import Counter
from pathlib import Path

import numpy as np


class DataPoint(t.Protocol):
    kind: str

    @classmethod
    def from_string_data(cls, data: list[str]) -> t.Self: ...

    def distance(self, other: t.Self) -> float: ...


class KNN[DP: DataPoint]:
    def __init__(self, data_point_type: type[DP], filepath: Path, has_header: bool = True) -> None:
        self.data_point_type = data_point_type
        self.data_points: list[DP] = []
        self._read_csv(filepath, has_header=has_header)

    def _read_csv(self, filepath: Path, has_header: bool) -> None:
        with filepath.open("r") as f:
            reader = csv.reader(f)
            if has_header:
                _ = next(reader)

            for row in reader:
                self.data_points.append(self.data_point_type.from_string_data(row))

    def nearest(self, k: int, data_point: DP) -> list[DP]:
        return sorted(self.data_points, key=data_point.distance)[:k]

    def classify(self, k: int, data_point: DP) -> str:
        neighbors = self.nearest(k, data_point)
        return Counter(neighbor.kind for neighbor in neighbors).most_common(1)[0][0]
