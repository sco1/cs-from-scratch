from __future__ import annotations

import argparse
from enum import StrEnum
from pathlib import Path


def clamp_int(num: int) -> int:
    """
    Imitate 8-bit unsigned integer overflow.

    Because Brainfuck can't change a value by more than `1` at a time, it is sufficient to
    explicitly to wrap to `0` and `255` when overflowing to the right and left, respectively.
    """
    if num > 255:
        return 0
    elif num < 0:
        return 255
    else:
        return num


class InvalidLoopError(Exception): ...  # noqa: D101


def parse_brackets(src: str) -> list[tuple[int, int]]:
    """
    Parse bracket pair opening & closing locations from the provided source.

    e.g.:
        * `,>,[<.>-]` -> `[(3, 8)]`
        * `[++[--]<<]` -> `[(3, 6), (0, 9)]`
    """
    stack = []
    matched = []
    for idx, c in enumerate(src):
        if c == "[":
            stack.append(idx)
        elif c == "]":
            try:
                open_idx = stack.pop()
            except IndexError:
                raise InvalidLoopError(
                    f"Closing bracket at idx={idx} has no corresponding opening"
                ) from None

            matched.append((open_idx, idx))

    if stack:
        raise InvalidLoopError(f"Opening bracket(s) have no corresponding closure: idx={stack}")

    return matched


class Instruction(StrEnum):  # noqa: D101
    SHIFT_RIGHT = ">"
    SHIFT_LEFT = "<"
    INCREMENT = "+"
    DECREMENT = "-"
    PRINT = "."
    READ = ","
    JUMP_IF_ZERO = "["
    JUMP_IF_NONZERO = "]"


class Brainfuck:  # noqa: D101
    cells: list[int]
    cell_idx: int
    pointer: int

    _src: str
    _n_cells: int

    _cache_loops: bool
    _bracket_map: dict[int, int]

    def __init__(self, src: str, n_cells: int = 30_000, cache_loops: bool = True) -> None:
        self._src = src
        self._n_cells = n_cells

        self._cache_loops = cache_loops
        if self._cache_loops:
            self._map_brackets()

    def _map_brackets(self) -> None:
        """Map mapped bracket pairs to a dictionary for downstream lookup."""
        matched = parse_brackets(self._src)

        # Map the matched pairs in both directions so end can be looked up by the start & vice-versa
        self._bracket_map = {}
        for b_start, b_end in matched:
            self._bracket_map[b_start] = b_end
            self._bracket_map[b_end] = b_start

    @classmethod
    def from_file(
        cls, filename: Path, n_cells: int = 30_000, cache_loops: bool = True
    ) -> Brainfuck:
        """
        Instantiate a Brainfuck program from the provided source file.

        `n_cells` may be optionally specified to control the number of cells available to the
        interpreter.
        """
        with open(filename, "r") as f:
            src = f.read().strip()

        return cls(src, n_cells=n_cells, cache_loops=cache_loops)

    def reset(self) -> None:  # noqa: D102
        self.cells = [0] * self._n_cells
        self.cell_idx = 0
        self.pointer = 0

    def find_bracket_match(self, start: int, forward: bool) -> int:
        """
        Locate the bracket that corresponds to the one at the provided `start` location.

        If searching for a closing bracket, use `forward=True`, otherwise locate the opening bracket
        using `forward=False`.
        """
        if forward:
            step = 1
            start_char = "["
            end_char = "]"
        else:
            step = -1
            start_char = "]"
            end_char = "["

        stack_count = 0
        loc = start + step
        while 0 <= loc < len(self._src):
            curr_char = self._src[loc]
            if curr_char == end_char:
                if stack_count == 0:
                    return loc
                else:
                    stack_count -= 1
            elif curr_char == start_char:
                stack_count += 1

            loc += step

        raise InvalidLoopError(f"No valid jump found (start: {start}, dir: {step})")

    def execute(self) -> None:
        """
        Execute the stored source code until completed.

        NOTE: Interpreter state is reset when this method is used, so any previous state will be
        lost.
        """
        self.reset()

        while self.pointer < len(self._src):
            raw_instruction = self._src[self.pointer]
            try:
                instruction = Instruction(raw_instruction)
            except ValueError:
                # Any characters that do not explicitly match an instruction are ignored
                self.pointer += 1
                continue

            match instruction:
                case Instruction.SHIFT_RIGHT:
                    self.cell_idx += 1
                case Instruction.SHIFT_LEFT:
                    self.cell_idx -= 1
                case Instruction.INCREMENT:
                    self.cells[self.cell_idx] = clamp_int(self.cells[self.cell_idx] + 1)
                case Instruction.DECREMENT:
                    self.cells[self.cell_idx] = clamp_int(self.cells[self.cell_idx] - 1)
                case Instruction.PRINT:
                    print(chr(self.cells[self.cell_idx]), end="", flush=True)
                case Instruction.READ:
                    self.cells[self.cell_idx] = clamp_int(int(input("?> ")))
                case Instruction.JUMP_IF_ZERO:
                    if self.cells[self.cell_idx] == 0:
                        if self._cache_loops:
                            self.pointer = self._bracket_map[self.pointer]
                        else:
                            self.pointer = self.find_bracket_match(self.pointer, forward=True)
                case Instruction.JUMP_IF_NONZERO:  # pragma: no branch
                    if self.cells[self.cell_idx] != 0:
                        if self._cache_loops:
                            self.pointer = self._bracket_map[self.pointer]
                        else:
                            self.pointer = self.find_bracket_match(self.pointer, forward=False)

            self.pointer += 1


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", nargs="?", type=Path)
    parser.add_argument("-s", "--source_str")
    parser.add_argument("-c", "--cells", type=int, default=30_000)
    args = parser.parse_args()

    if (args.filename is not None) and (args.source_str is not None):
        print("ERROR: Source file and source string cannot both be specified.")
        return
    elif (args.filename is None) and (args.source_str is None):
        print("ERROR: Must specify a source file or a source string.")
        return

    if args.filename is not None:
        bf = Brainfuck.from_file(args.filename, n_cells=args.cells)
    elif args.source_str is not None:
        bf = Brainfuck(args.source_str, n_cells=args.cells)

    bf.execute()


if __name__ == "__main__":
    main()
