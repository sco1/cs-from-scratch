from pathlib import Path

from cs_from_scratch.NanoBASIC.interpreter import Interpreter
from cs_from_scratch.NanoBASIC.parser import Parser
from cs_from_scratch.NanoBASIC.tokenizer import tokenize


class NanoBASICRuntime:
    def __init__(self, filepath: Path) -> None:
        with filepath.open("r") as f:
            self.tokens = tokenize(f)

        self.ast = Parser(self.tokens).parse()

    def execute(self) -> None:
        Interpreter(self.ast).run()
