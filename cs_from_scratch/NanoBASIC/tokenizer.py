import io
import re
import typing as t
from dataclasses import dataclass
from enum import Enum

from cs_from_scratch.NanoBASIC import errors

ASSOCIATED_VAL_T: t.TypeAlias = str | int | None


class TokenType(Enum):
    """
    NanoBASIC's accepted token types.

    Each token is enumerated as a tuple whose first component is the matching regular expression and
    second component is whether the token has an associated value.
    """

    COMMENT = (r"rem.*", False)
    WHITESPACE = (r"[ \t\n\r]", False)

    PRINT = (r"print", False)
    IF_T = (r"if", False)
    THEN = (r"then", False)
    GOTO = (r"goto", False)
    INPUT = (r"input", False)
    LET = (r"let", False)
    GOSUB = (r"gosub", False)
    RETURN_T = (r"return", False)

    # For REPL only, do not get nodes
    CLEAR = (r"clear", False)
    LIST = (r"list", False)
    RUN = (r"run", False)
    END = (r"end", False)

    COMMA = (r",", False)
    EQUAL = (r"=", False)
    NOT_EQUAL = (r"<>|><", False)
    LESS_EQUAL = (r"<=", False)
    GREATER_EQUAL = (r">=", False)
    LESS = (r"<", False)
    GREATER = (r">", False)
    PLUS = (r"\+", False)
    MINUS = (r"-", False)
    MULTIPLY = (r"\*", False)
    DIVIDE = (r"/", False)
    OPEN_PAREN = (r"\(", False)
    CLOSE_PAREN = (r"\)", False)
    VARIABLE = (r"[A-Za-z_]+", True)
    NUMBER = (r"-?[0-9]+", True)
    STRING = (r'"(?:\\.|[^"\\])*"', True)

    def __init__(self, pattern: str, has_associated_value: bool) -> None:
        self.pattern = pattern
        self.has_associated_value = has_associated_value

    def __repr__(self) -> str:
        return self.name


BOOLEAN_OPERATORS = {
    TokenType.GREATER,
    TokenType.GREATER_EQUAL,
    TokenType.EQUAL,
    TokenType.NOT_EQUAL,
    TokenType.LESS,
    TokenType.LESS_EQUAL,
}

REPL_ONLY = {
    TokenType.CLEAR,
    TokenType.LIST,
    TokenType.RUN,
    TokenType.END,
}


@dataclass(frozen=True)
class Token:  # noqa: D101
    kind: TokenType
    lineno: int
    col_start: int
    col_end: int
    associated_value: ASSOCIATED_VAL_T


def tokenize(src: t.TextIO | str) -> list[Token]:  # noqa: D103
    if isinstance(src, io.IOBase):
        src_lines = src.readlines()
    elif isinstance(src, str):
        src_lines = src.splitlines()
    else:
        raise ValueError()

    tokens = []
    for lineno, line in enumerate(src_lines, start=1):
        col_start = 1
        while len(line) > 0:
            found = None
            for tok in TokenType:
                found = re.match(tok.pattern, line, re.IGNORECASE)
                if found:
                    col_end = col_start + found.end() - 1
                    if (tok is not TokenType.WHITESPACE) and (tok is not TokenType.COMMENT):
                        associated_value: ASSOCIATED_VAL_T = None
                        if tok.has_associated_value:
                            if tok is TokenType.NUMBER:
                                associated_value = int(found.group(0))
                            elif tok is TokenType.VARIABLE:
                                associated_value = found.group()
                            elif tok is TokenType.STRING:
                                associated_value = found.group(0)[1:-1]

                        tokens.append(
                            Token(
                                kind=tok,
                                lineno=lineno,
                                col_start=col_start,
                                col_end=col_end,
                                associated_value=associated_value,
                            )
                        )

                    line = line[found.end() :]
                    col_start = col_end + 1
                    break

            if not found:
                raise errors.TokenizationError("Unknown token.", lineno=lineno, col=col_start)

    return tokens
