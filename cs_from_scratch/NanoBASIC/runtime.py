from pathlib import Path

from cs_from_scratch.NanoBASIC import nodes
from cs_from_scratch.NanoBASIC.errors import ParserError, TokenizationError
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
        out_filename = f"{self.filepath.stem}_AST.txt"
        out_filepath = self.filepath.parent / out_filename

        with out_filepath.open("w") as f:
            f.writelines((f"{s!r}\n" for s in self.ast))

    def execute(self) -> None:  # noqa: D102
        Interpreter(self.ast).run()


class NanoBASICREPL:
    """
    The NanoBASIC REPL.

    When the REPL is entered, the user is prompted to input one valid NanoBASIC line at a time. If
    the line fails to parse, the error is displayed and the line is ignored.

    The following REPL-specific statements are also provided:
        * `CLEAR` - Clear all entered lines
        * `LIST` - List all entered lines
        * `RUN` - Run the entered program
        * `END` - End the REPL session
    """

    def __init__(self) -> None:
        self.ast: list[nodes.Statement] = []

    def _list(self) -> None:
        for s in self.ast:
            print(s)

    def _clear(self) -> None:
        self.ast = []

    def _exec(self) -> None:
        Interpreter(self.ast).run()

    def run(self) -> None:  # noqa: D102
        print("Welcome to the NanoBASIC REPL!")
        while True:
            try:
                line = input(">>> ")
            except KeyboardInterrupt:
                break

            try:
                ast = Parser(tokenize(line)).parse()
            except (ParserError, TokenizationError) as e:
                print(f"{type(e).__name__} - {e}")
                continue

            if isinstance(ast[0], nodes.REPL_NODES_T):
                match ast[0]:
                    case nodes.REPLClear():
                        self._clear()
                    case nodes.REPLList():
                        self._list()
                    case nodes.REPLRun():
                        self._exec()
                    case nodes.REPLEnd():
                        break
            else:
                self.ast.extend(ast)

        print("\nSmell you later!")
