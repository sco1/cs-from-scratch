from cs_from_scratch.NanoBASIC.nodes import Node
from cs_from_scratch.NanoBASIC.tokenizer import Token


class NanoBASICError(Exception):
    def __init__(self, msg: str, lineno: int, col: int) -> None:
        super().__init__(msg)

        self.msg = msg
        self.lineno = lineno
        self.col = col

    def __str__(self) -> str:
        return f"{self.lineno}:{self.col} - {self.msg}"


class ParserError(NanoBASICError):
    def __init__(self, msg: str, token: Token):
        super().__init__(msg=msg, lineno=token.lineno, col=token.col_start)


class InterpreterError(NanoBASICError):
    def __init__(self, msg: str, node: Node):
        super().__init__(msg=msg, lineno=node.lineno, col=node.col_start)
