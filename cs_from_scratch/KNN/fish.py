import typing as t
from dataclasses import dataclass

from cs_from_scratch.KNN.knn import DataPoint


@dataclass
class Fish(DataPoint):
    """
    Represent data points from Pekka Brofeldt's fish stock dataset.

    See: Pekka Brofeldt, "Bidrag till kaennedom on fiskbestondet i vaara sjoear Laengelmaevesi,"
    T.H.Jaervi: Finlands Fiskeriet Band 4, Meddelanden utgivna av fiskerifoereningen i Finland,
    Helsingfors, 1917.
    """

    kind: str
    weight: float
    length1: float
    length2: float
    length3: float
    height: float
    width: float

    @classmethod
    def from_string_data(cls, data: list[str]) -> t.Self:
        """
        Parse a data row from the fish dataset.

        Data is assumed to be a CSV whose rows are of the form:
            `Species, Weight, Length1, Length2, Length3, Height, Width`
        """
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
        """Determine the euclidian distance between two fish points."""
        return (  # type: ignore[no-any-return]
            (self.length1 - other.length1) ** 2
            + (self.length2 - other.length2) ** 2
            + (self.length3 - other.length3) ** 2
            + (self.height - other.height) ** 2
            + (self.width - other.width) ** 2
        ) ** 0.5
