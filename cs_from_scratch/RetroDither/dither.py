import itertools
import typing as t
from array import array

from PIL import Image

DITHER_THRESH = 127


class PatternPart(t.NamedTuple):  # noqa: D101
    dc: int
    dr: int
    numerator: int
    denominator: int


# Atkinson dithering error diffusion
#      -1  0   1   2
# -------------------
# 0 |      X  1/8 1/8
# 1 | 1/8 1/8 1/8
# 2 |     1/8
ATKINSON = [
    PatternPart(dc=1, dr=0, numerator=1, denominator=8),
    PatternPart(dc=2, dr=0, numerator=1, denominator=8),
    PatternPart(dc=-1, dr=1, numerator=1, denominator=8),
    PatternPart(dc=0, dr=1, numerator=1, denominator=8),
    PatternPart(dc=1, dr=1, numerator=1, denominator=8),
    PatternPart(dc=0, dr=2, numerator=1, denominator=8),
]

# Floyd-Steinberg dithering error diffusion
#      -1   0     1
# ------------------
# 0 |       X   7/16
# 1 | 3/16 5/16 1/16
FLOYD_STEINBERG = [
    PatternPart(dc=1, dr=0, numerator=7, denominator=16),
    PatternPart(dc=-1, dr=1, numerator=3, denominator=16),
    PatternPart(dc=0, dr=1, numerator=5, denominator=16),
    PatternPart(dc=1, dr=1, numerator=1, denominator=16),
]


def dither(
    img: Image.Image, threshold: int = DITHER_THRESH, pattern: list[PatternPart] = ATKINSON
) -> array:
    """
    Apply the specified error-diffusion dithering algorithm to the input image.

    Return is an array of dithered pixels (`255` for white, `0` for black).

    `threshold` may be specified to control the behavior of the algorithm; this threshold controls
    the shift from grayscale to black/white, e.g. for the default threshold of `127` any pixel
    greater than 127 is marked as white, and any pixel less than or equal to 127 is marked as black.

    NOTE: It is assumed that the image is provided as grayscale (PIL mode `"L"`).
    """

    def diffuse(c: int, r: int, err: int) -> None:
        """Distribute the pixel's error to adjacent pixels, as defined by the specified pattern."""
        for part in pattern:
            col = c + part.dc
            row = r + part.dr

            if (col < 0) or (col >= img.width) or (row >= img.height):  # bounds check
                continue

            current_pixel: float = img.getpixel((col, row))  # type: ignore[assignment]
            error_part = (err * part.numerator) // (part.denominator)
            img.putpixel((col, row), current_pixel + error_part)

    # The general algorithm for each pixel is as follows:
    #     1. Find whether the pixel is closer to black or white, managed by the specified threshold,
    #        and shift it to this color
    #     2. Calculate the difference between the new pixel color and its original color, which
    #        defines the error to be diffused to the surrounding pixels
    #     3. Diffuse the error to the surrounding pixels according to the specified diffusion
    #        pattern
    res = array("B", [0] * (img.width * img.height))
    for x, y in itertools.product(range(img.width), range(img.height)):
        old_pixel: float = img.getpixel((x, y))  # type: ignore[assignment]
        if old_pixel > threshold:
            new_pixel = 255
        else:
            new_pixel = 0

        res[y * img.width + x] = new_pixel
        diff = int(old_pixel - new_pixel)
        diffuse(x, y, diff)

    return res
