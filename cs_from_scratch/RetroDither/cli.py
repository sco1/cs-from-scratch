import argparse
from pathlib import Path

from PIL import Image

from cs_from_scratch.RetroDither.dither import DITHER_MAPPING, dither
from cs_from_scratch.RetroDither.macpaint import prepare_img, write_macpaint


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser("RetroDither")
    parser.add_argument("input_img", type=Path, help="Input image file.")
    parser.add_argument(
        "-a",
        "--algorithm",
        choices=DITHER_MAPPING.keys(),
        default="atkinson",
        help="Error diffusion algorithm",
    )
    parser.add_argument("-g", "--gif", action="store_true", help="Create an output GIF.")
    args = parser.parse_args()

    in_filepath: Path = args.input_img
    img = prepare_img(in_filepath)
    dithered = dither(img, pattern=DITHER_MAPPING[args.algorithm])

    out_filepath = in_filepath.with_suffix(".bin")
    write_macpaint(dithered, out_filepath=out_filepath, width=img.width, height=img.height)

    if args.gif:
        out_gif = Image.frombytes("L", img.size, dithered.tobytes())
        out_gif.save(in_filepath.with_suffix(".gif"))


if __name__ == "__main__":  # noqa: D103
    main()
