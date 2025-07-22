from collections import deque

from cs_from_scratch.NanoBASIC import nodes
from cs_from_scratch.NanoBASIC.errors import InterpreterError


class Interpreter:
    def __init__(self, statements: list[nodes.Statement]) -> None:
        self.statements = statements
        self.variable_table: dict[str, int] = {}
        self.statement_idx = 0
        self.subroutine_stack: deque[int] = deque()

    @property
    def current(self) -> nodes.Statement:
        return self.statements[self.statement_idx]

    def run(self) -> None:
        raise NotImplementedError
