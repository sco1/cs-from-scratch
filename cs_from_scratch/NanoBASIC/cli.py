import argparse
from pathlib import Path

from cs_from_scratch.NanoBASIC.runtime import NanoBASICRuntime


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser("NanoBASIC")
    parser.add_argument("filepath", type=Path)
    parser.add_argument("--dump_ast", action="store_true")
    args = parser.parse_args()

    runtime = NanoBASICRuntime(args.filepath)

    if args.dump_ast:
        runtime.write_ast()

    runtime.execute()


if __name__ == "__main__":  # noqa: D103
    main()
