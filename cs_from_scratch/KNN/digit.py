import typing as t
from dataclasses import dataclass

import numpy as np

from cs_from_scratch.KNN.knn import DataPoint


@dataclass
class Digit(DataPoint):
    """
    Represent data points from the Kaynak & Alpaydin digits dataset.

    See: Ethem Alpaydin and Cenk Kaynak, “Optical Recognition of Handwritten Digits,” UCI Machine
    Learning Repository, accessed December 10, 2024, https://doi.org/10.24432/C50P49
    """

    kind: str
    pixels: np.ndarray

    @classmethod
    def from_string_data(cls, data: list[str]) -> t.Self:
        """
        Parse a data row from the digits dataset.

        Data is assumed to be a CSV whose rows contain `64` integers corresponding to the grayscale
        level of each pixel of the `8x8` digit image, followed by an integer representing the digit
        (`0-9`) that the image should be classified as.
        """
        return cls(kind=data[64], pixels=np.array(data[:64], dtype=np.uint32))

    def distance(self, other: t.Self) -> float:
        """Determine the euclidian distance between two digit points."""
        tmp = self.pixels - other.pixels
        return np.sqrt(np.dot(tmp.T, tmp))  # type: ignore[no-any-return]
