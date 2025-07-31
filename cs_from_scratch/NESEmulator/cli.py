import argparse
from pathlib import Path

from cs_from_scratch.NESEmulator.console import run
from cs_from_scratch.NESEmulator.rom import ROM


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser("NESEmulator")
    parser.add_argument("rom_file", type=Path, help="An iNES game file.")
    args = parser.parse_args()

    run(ROM(args.rom_file), args.rom_file.stem)


if __name__ == "__main__":  # noqa: D103
    main()
