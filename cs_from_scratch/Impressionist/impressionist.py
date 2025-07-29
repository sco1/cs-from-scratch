from __future__ import annotations

import math
import operator
import random
import timeit
import typing as t
from enum import StrEnum
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

from cs_from_scratch.Impressionist import COLOR_T, COORDS_T, Coord
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


class BoundingBox(t.NamedTuple):  # noqa: D101
    min_x: int
    min_y: int
    max_x: int
    max_y: int

    @classmethod
    def from_coords(cls, coords: COORDS_T) -> BoundingBox:  # noqa: D102
        return cls(
            min_x=min(coords, key=operator.itemgetter(0)).x,
            min_y=min(coords, key=operator.itemgetter(1)).y,
            max_x=max(coords, key=operator.itemgetter(0)).x,
            max_y=max(coords, key=operator.itemgetter(1)).y,
        )


def get_most_common_color(img: Image.Image) -> COLOR_T:  # noqa: D103
    colors = img.getcolors(img.width * img.height)  # Provides (count, color) tuples

    if colors is None:
        raise ValueError

    return max(colors, key=operator.itemgetter(0))[1]  # type: ignore[return-value]


def get_average_color(img: Image.Image) -> COLOR_T:  # noqa: D103
    return tuple(round(n) for n in ImageStat.Stat(img).mean)  # type: ignore[return-value]


def get_aspect_ratio(img: Image.Image) -> float:  # noqa: D103
    width, height = img.size
    return width / height


class Impressionist:
    """The Impressionist stochastic painter."""

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
        """
        Build a new instance of the Impressionist stochastic painter using the specified parameters.

        If `vector` is `True`, an SVG is output alongside the final image.

        If `animation_length` is `>0`, an animated GIF will be generated alongside the final image,
        iterating through the trial steps with a frame length of `animation_length` milliseconds.

        NOTE: The `length` parameter corresponds to the output file height, but is named `length`
        for CLI argument deconfliction.
        """
        self.img_filepath = img_filepath

        self.method = method
        self.shape_type = shape_type

        self.n_trials = n_trials

        self.length = length
        self.vector = vector
        self.animation_length = animation_length

        with self.img_filepath.open("rb") as f:
            self.original = Image.open(f).convert("RGB")

        # Scale down image for faster processing
        aspect_ratio = get_aspect_ratio(self.original)
        new_size = (int(MAX_HEIGHT * aspect_ratio), MAX_HEIGHT)
        self.original.thumbnail(new_size, Image.Resampling.LANCZOS)

        # Generate the new canvas background using the average color of the original
        avg_color = get_average_color(self.original)
        self.glass = Image.new("RGB", new_size, avg_color)

        self.shapes: list[tuple[COORDS_T, COLOR_T]] = []
        self.best_diff = self._difference(self.glass)

    def _difference(self, other: Image.Image) -> float:
        """
        Calculate the similarity score between the current image & the query image.

        Similarity is calculated by averaging the per-pixel differences between the two images and
        is reported as a ratio.
        """
        diff = ImageChops.difference(self.original, other)
        stat = ImageStat.Stat(diff)
        diff_ratio = sum(stat.mean) / (len(stat.mean) * 255)

        return diff_ratio

    def _random_coordinates(self) -> COORDS_T:
        """Generate a random location for the painter's specified `ShapeType`."""
        match self.shape_type:
            case ShapeType.ELLIPSE | ShapeType.LINE:
                n_points = 2
            case ShapeType.TRIANGLE:
                n_points = 3
            case ShapeType.QUADRILATERAL:
                n_points = 4

        return [
            Coord(
                x=random.randint(0, self.original.width), y=random.randint(0, self.original.height)
            )
            for _ in range(n_points)
        ]

    def _trial(self) -> None:
        """
        Execute a step of the stochastic painting algorithm.

        Each step of the algorithm attempts to place one shape onto the canvas; if the new shape
        brings the canvas closer to the original image then it is kept for the next iteration.
        Within each trial, an attempt is made to nudge the shape's coordinates to see if any
        improvement can be made.
        """
        while True:
            # There is a chance that random_coordinates can generate points that are entirely along
            # an axis, so as a hack we can generate coordinates until this isn't the case
            coords = self._random_coordinates()
            bbox = BoundingBox.from_coords(coords)
            region = self.original.crop(bbox)
            if (region.width > 0) and (region.height > 0):
                break

        color: COLOR_T
        match self.method:
            case ColorMethod.AVERAGE:
                color = get_average_color(region)
            case ColorMethod.COMMON:
                color = get_most_common_color(region)
            case ColorMethod.RANDOM:
                color = tuple(random.choices(range(256), k=3))  # type: ignore[assignment]

        original = self.glass

        def experiment() -> bool:
            """
            Check if the attempt to draw a new shape is successful.

            Success is determined by whether or not the difference between the working and original
            images has been lowered.
            """
            new_img = original.copy()
            glass_draw = ImageDraw.Draw(new_img)

            if self.shape_type == ShapeType.ELLIPSE:
                glass_draw.ellipse(bbox, fill=color)
            else:
                glass_draw.polygon(coords, fill=color)

            new_diff = self._difference(new_img)
            if new_diff < self.best_diff:
                self.best_diff = new_diff
                self.glass = new_img
                return True

            return False

        if experiment():
            # If we have at least a good starting point, attempt to nudge the shape location to see
            # if any further improvements can be made
            for idx in range(len(coords)):
                for delta in (-1, 1):
                    while True:
                        old_coords = coords.copy()
                        coords[idx] = coords[idx].shift(delta)
                        if not experiment():
                            coords = old_coords
                            break

            self.shapes.append((coords, color))

    def run_trials(self) -> None:
        """Execute the configured number of drawing trials & write the output to disk."""
        last_percent = 0
        start = timeit.default_timer()
        for trial_idx in range(self.n_trials):
            self._trial()
            completion = math.trunc((trial_idx / self.n_trials) * 100)

            if completion > last_percent:
                last_percent = completion
                msg = f" {completion}% done, best difference: {self.best_diff:0.4f}"
                print(f"{msg}", end="\r", flush=True)

        end = timeit.default_timer()
        print(f"Trials complete! Best difference: {self.best_diff:0.4f}")
        print(f"{end - start:0.2f} seconds elapsed. {len(self.shapes)} shapes created.")
        self.create_output()

    def create_output(self) -> None:
        """
        Write the painting results to disk.

        The output file(s) will retain the base name of the input image with an added `_impression`
        suffix.

        If `self.vector` is `True`, an SVG is output alongside the final image.

        If `self.animation_length` is `>0`, an animated GIF will be generated alongside the final
        image, iterating through the trial steps with a frame length of `self.animation_length`
        milliseconds.
        """
        # Scale the image from its working size to the user-specified size for final output
        avg_color = get_average_color(self.original)
        original_width, original_height = self.original.size
        ratio = self.length / original_height
        output_size = (int(original_width * ratio), int(original_height * ratio))

        output_img = Image.new("RGB", output_size, avg_color)
        output_draw = ImageDraw.Draw(output_img)

        if self.vector:
            svg = SVG(*output_size, avg_color)
        else:
            svg = None

        animation_frames: list[Image.Image] | None
        if self.animation_length > 0:
            animation_frames = []
        else:
            animation_frames = None

        for coords, color in self.shapes:
            scaled_coords = [c.scale(ratio) for c in coords]
            bbox = BoundingBox.from_coords(scaled_coords)
            if self.shape_type == ShapeType.ELLIPSE:
                output_draw.ellipse(bbox, fill=color)
                if svg is not None:
                    svg.draw_ellipse(*scaled_coords, color=color)  # type: ignore[arg-type, misc]
            else:
                output_draw.polygon(scaled_coords, fill=color)
                if svg is not None:
                    if self.shape_type == ShapeType.LINE:
                        svg.draw_line(*scaled_coords, color=color)  # type: ignore[arg-type, misc]
                    else:
                        svg.draw_polygon(scaled_coords, color=color)

            if animation_frames is not None:
                animation_frames.append(output_img.copy())

        outfile_stem = f"{self.img_filepath.stem}_impression"
        output_filepath = self.img_filepath.with_stem(outfile_stem)

        print("Writing final image...", end="")
        output_img.save(output_filepath)
        print("Done!")

        if svg is not None:
            svg_filepath = output_filepath.with_suffix(".svg")

            print("Writing SVG...", end="")
            svg.write(svg_filepath)
            print("Done!")

        if animation_frames is not None:
            gif_filepath = output_filepath.with_suffix(".gif")

            print("Writing GIF...", end="", flush=True)
            animation_frames[0].save(
                gif_filepath,
                save_all=True,
                append_images=animation_frames[1:],
                optimize=False,
                duration=self.animation_length,
                loop=0,
                transparency=0,
                disposal=2,
            )
            print("Done!")
