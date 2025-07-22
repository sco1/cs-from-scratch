from pathlib import Path

from cs_from_scratch.NanoBASIC.interpreter import Interpreter
from cs_from_scratch.NanoBASIC.parser import Parser
from cs_from_scratch.NanoBASIC.tokenizer import tokenize


class NanoBASICRuntime:  # noqa: D101
    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath

        with self.filepath.open("r") as f:
            self.tokens = tokenize(f)

        self.ast = Parser(self.tokens).parse()

    def write_ast(self) -> None:
        """
        Write the parsed AST to a text file.

        The AST is written to a `<filename>_AST.txt` file in the same directory as the loaded source
        file.

        NOTE: Any existing file of the same name will be overwritten.
        """
        # TODO: Come up with a prettier way to represent the AST
        out_filename = f"{self.filepath.stem}_AST.txt"
        out_filepath = self.filepath.parent / out_filename

        with out_filepath.open("w") as f:
            f.writelines((f"{s!r}\n" for s in self.ast))

    def execute(self) -> None:  # noqa: D102
        Interpreter(self.ast).run()
