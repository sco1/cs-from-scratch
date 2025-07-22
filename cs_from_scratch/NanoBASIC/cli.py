import argparse
from pathlib import Path

from cs_from_scratch.NanoBASIC.runtime import NanoBASICRuntime


def main() -> None:
    parser = argparse.ArgumentParser("NanoBASIC")
    parser.add_argument("filepath", type=Path)
    args = parser.parse_args()

    runtime = NanoBASICRuntime(args.filepath)
    runtime.execute()


if __name__ == "__main__":  # noqa: D103
    main()
