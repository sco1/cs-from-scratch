import argparse
from pathlib import Path

from cs_from_scratch.Impressionist.impressionist import ColorMethod, Impressionist, ShapeType


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser("Impressionist")
    parser.add_argument("input_img", type=Path, help="Input image file.")
    parser.add_argument("-t", "--trials", type=int, default=10_000, help="Number of trials to run.")
    parser.add_argument(
        "-m",
        "--method",
        type=ColorMethod,
        choices=ColorMethod,
        default=ColorMethod.AVERAGE,
        help="Method for determining shape colors.",
    )
    parser.add_argument(
        "-s",
        "--shape",
        type=ShapeType,
        choices=ShapeType,
        default=ShapeType.ELLIPSE,
        help="Base shape type.",
    )
    parser.add_argument(
        "-l", "--length", type=int, default=256, help="Pixel height of final image."
    )
    parser.add_argument("-v", "--vector", action="store_true", help="Create a vector output.")
    parser.add_argument(
        "-a",
        "--animate",
        type=int,
        default=0,
        help="If >0, create an animated GIF of n ms per frame.",
    )
    args = parser.parse_args()

    impr = Impressionist(
        img_filepath=args.input_img,
        n_trials=args.trials,
        method=args.method,
        shape_type=args.shape,
        length=args.length,
        vector=args.vector,
        animation_length=args.animate,
    )
    impr.run_trials()


if __name__ == "__main__":  # noqa: D103
    main()
