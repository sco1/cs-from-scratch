import math
import operator
import random
import timeit
from enum import StrEnum
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

from cs_from_scratch.Impressionist import COLOR_T, COORDS_T
from cs_from_scratch.Impressionist.svg import SVG

MAX_HEIGHT = 256


class ColorMethod(StrEnum):  # noqa: D101
    RANDOM = "random"
    AVERAGE = "average"
    COMMON = "common"


class ShapeType(StrEnum):  # noqa: D101
    ELLIPSE = "ellipse"
    TRIANGLE = "triangle"
    QUADRILATERAL = "quadrilateral"
    LINE = "line"


def get_most_common_color(img: Image.Image) -> COLOR_T:  # noqa: D103
    colors = img.getcolors(img.width * img.height)  # Provides (count, color) tuples

    if colors is None:
        raise ValueError

    return max(colors, key=operator.itemgetter(0))[1]  # type: ignore[return-value]


class Impressionist:
    def __init__(
        self,
        img_filepath: Path,
        n_trials: int,
        method: ColorMethod,
        shape_type: ShapeType,
        length: int,
        vector: bool,
        animation_length: int,
    ) -> None:
        self.method = method
        self.shape_type = shape_type

        self.n_trials = n_trials

        self.length = length
        self.vector = vector
        self.animation_length = animation_length

        with img_filepath.open("rb") as f:
            self.original = Image.open(f).convert("RGB")

        # Scale down image for faster processing
        width, height = self.original.size
        aspect_ratio = width / height
        new_size = (int(MAX_HEIGHT * aspect_ratio), MAX_HEIGHT)
        self.original.thumbnail(new_size, Image.Resampling.LANCZOS)

        # Generate the new canvas background using the average color of the original
        avg_color = tuple((round(n) for n in ImageStat.Stat(self.original).mean))
        self.glass = Image.new("RGB", new_size, avg_color)

        self.shapes = []
        self.best_diff = self.difference(self.glass)

    def difference(self, other: Image.Image) -> float:
        diff = ImageChops.difference(self.original, other)
        stat = ImageStat.Stat(diff)
        diff_ratio = sum(stat.mean) / (len(stat.mean) * 255)

        return diff_ratio

    def run_trials(self) -> None:
        last_percent = 0
        start = timeit.default_timer()
        for trial_idx in range(self.n_trials):
            self.trial()
            completion = math.trunc((trial_idx / self.n_trials) * 100)

            if completion > last_percent:
                last_percent = completion
                print(f"{completion}% done, best difference: {self.best_diff}")

        end = timeit.default_timer()
        print(f"{end - start} seconds elapsed. {len(self.shapes)} shapes created.")
        self.create_output()

    def trial(self) -> None:
        raise NotImplementedError

    def create_output(self) -> None:
        raise NotImplementedError
