import argparse
from pathlib import Path

from cs_from_scratch.NanoBASIC.runtime import NanoBASICREPL, NanoBASICRuntime


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser("NanoBASIC")
    parser.add_argument("filepath", type=Path, nargs="?", default=None)
    parser.add_argument("--dump_ast", action="store_true")
    args = parser.parse_args()

    if args.filepath is not None:
        rt = NanoBASICRuntime(args.filepath)

        if args.dump_ast:
            rt.write_ast()

        rt.execute()
    else:
        repl = NanoBASICREPL()
        repl.run()


if __name__ == "__main__":  # noqa: D103
    main()
