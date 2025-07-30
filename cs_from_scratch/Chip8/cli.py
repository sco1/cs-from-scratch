import argparse
from pathlib import Path

from cs_from_scratch.Chip8.vm import run


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser("Chip8")
    parser.add_argument("rom_file", type=Path, help="A CHIP-8 ROM File.")
    args = parser.parse_args()

    with args.rom_file.open("rb") as f:
        rom_data = f.read()

    run(rom_data, args.rom_file.stem)


if __name__ == "__main__":  # noqa: D103
    main()
