import csv
import typing as t
from collections import Counter
from pathlib import Path

import numpy as np


class DataPoint(t.Protocol):  # noqa: D101
    kind: str

    @classmethod
    def from_string_data(cls, data: list[str]) -> t.Self: ...  # noqa: D102

    def distance(self, other: t.Self) -> float: ...  # noqa: D102


class KNN[DP: DataPoint]:
    """
    KNN Manager.

    Contained data is assumed to be of a single type, and is responsible for implementing methods in
    accordance with the `DataPoint` protocol.
    """

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
        """Identify the `k` nearest data points to the query data point."""
        return sorted(self.data_points, key=data_point.distance)[:k]

    def classify(self, k: int, data_point: DP) -> str:
        """Classify the query data point according to the `k` nearest data points."""
        neighbors = self.nearest(k, data_point)
        return Counter(neighbor.kind for neighbor in neighbors).most_common(1)[0][0]

    def predict(self, k: int, data_point: DP, property_name: str) -> float:
        """Predict a property of the query point according to the `k` nearest data points."""
        neighbors = self.nearest(k, data_point)
        predicted = sum([getattr(neighbor, property_name) for neighbor in neighbors]) / len(
            neighbors
        )
        return predicted  # type: ignore[no-any-return]

    def predict_array(self, k: int, data_point: DP, property_name: str) -> np.ndarray:
        """Predict a numpy array property of the query point via the `k` nearest data points."""
        neighbors = self.nearest(k, data_point)
        predicted = np.sum(
            [getattr(neighbor, property_name) for neighbor in neighbors], axis=0
        ) / len(neighbors)
        return predicted  # type: ignore[no-any-return]
