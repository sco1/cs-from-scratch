from enum import StrEnum
from pathlib import Path


def clamp_int(num: int) -> int:
    if num > 255:
        return 0
    elif num < 0:
        return 255
    else:
        return num


class UnknownInstructionError(Exception): ...


class InvalidJumpError(Exception): ...


class Instruction(StrEnum):
    SHIFT_RIGHT = ">"
    SHIFT_LEFT = "<"
    INCREMENT = "+"
    DECREMENT = "-"
    PRINT = "."
    READ = ","
    JUMP_IF_ZERO = "["
    JUMP_IF_NONZERO = "]"


class Brainfuck:
    cells: list[int]
    cell_idx: int
    pointer: int

    _src: str

    def __init__(self, filename: str | Path) -> None:
        # TODO: Swap to classmethods that accept either a string source or a Path input
        # TODO: Add specifiers for cell count and n cell bits
        with open(filename, "r") as f:
            self._src = f.read().strip()

    def reset(self) -> None:
        self.cells = [0] * 30000
        self.cell_idx = 0
        self.pointer = 0

    def find_bracket_match(self, start: int, forward: bool) -> int:
        # TODO: Use a stack-based parser that we can run on init
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

        raise InvalidJumpError(f"No valid jump found (start: {start}, dir: {step})")

    def execute(self) -> None:
        self.reset()

        while self.pointer < len(self._src):
            raw_instruction = self._src[self.pointer]
            try:
                instruction = Instruction(raw_instruction)
            except ValueError:
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
                    self.cells[self.cell_idx] = clamp_int(int(input()))
                case Instruction.JUMP_IF_ZERO:
                    if self.cells[self.cell_idx] == 0:
                        self.pointer = self.find_bracket_match(self.pointer, forward=True)
                case Instruction.JUMP_IF_NONZERO:
                    if self.cells[self.cell_idx] != 0:
                        self.pointer = self.find_bracket_match(self.pointer, forward=False)

            self.pointer += 1


if __name__ == "__main__":
    # TODO: Add CLI entry & argument parsing
    bf = Brainfuck(Path("./examples/brainfuck/fibonacci.bf"))
    bf.execute()
