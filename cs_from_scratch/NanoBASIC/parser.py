import typing as t

from cs_from_scratch.NanoBASIC import nodes
from cs_from_scratch.NanoBASIC.errors import ParserError
from cs_from_scratch.NanoBASIC.tokenizer import Token, TokenType


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.token_idx = 0

    @property
    def exhausted(self) -> bool:
        return self.token_idx >= len(self.tokens)

    @property
    def previous(self) -> Token:
        return self.tokens[self.token_idx - 1]

    @property
    def current(self) -> Token:
        if self.exhausted:
            raise ParserError(f"No tokens after {self.previous.kind}", self.previous)

        return self.tokens[self.token_idx]

    def consume(self, kind: TokenType) -> Token:
        if self.current.kind is kind:
            self.token_idx += 1
            return self.previous

        raise ParserError(
            f"Expected {kind} after {self.previous} but got {self.current}", self.current
        )

    def parse(self) -> list[nodes.Statement]:
        statements = []
        while not self.exhausted:
            statement = self.parse_line()
            statements.append(statement)

        return statements

    def parse_line(self) -> nodes.Statement:
        line_id = self.consume(TokenType.NUMBER)
        return self.parse_statement(t.cast(int, line_id.associated_value))

    def parse_statement(self, line_id: int) -> nodes.Statement:
        match self.current.kind:
            case TokenType.PRINT:
                return self.parse_print(line_id)
            case TokenType.IF_T:
                return self.parse_if(line_id)
            case TokenType.LET:
                return self.parse_let(line_id)
            case TokenType.GOTO:
                return self.parse_goto(line_id)
            case TokenType.GOSUB:
                return self.parse_gosub(line_id)
            case TokenType.RETURN_T:
                return self.parse_return(line_id)
            case _:
                raise ParserError("Expected to find start of statement", self.current)

    def parse_print(self, line_id: int) -> nodes.PrintStmt:
        tok = self.consume(TokenType.PRINT)
        printables: list[str | nodes.NumericExpr] = []

        while True:
            if self.current.kind is TokenType.STRING:
                string_tok = self.consume(TokenType.STRING)
                printables.append(t.cast(str, string_tok.associated_value))
            elif (expr := self.parse_numeric_expression()) is not None:
                printables.append(expr)
            else:
                raise ParserError(
                    "PRINT statements may only contain strings or numeric expressions", self.current
                )

            if not self.exhausted and (self.current.kind is TokenType.COMMA):
                self.consume(TokenType.COMMA)
                continue

            break

        return nodes.PrintStmt(
            line_id=line_id,
            lineno=tok.lineno,
            col_start=tok.col_start,
            col_end=tok.col_end,
            printables=printables,
        )

    def parse_if(self, line_id: int) -> nodes.IfStmt:
        raise NotImplementedError

    def parse_let(self, line_id: int) -> nodes.LetStmt:
        raise NotImplementedError

    def parse_goto(self, line_id: int) -> nodes.GoToStmt:
        raise NotImplementedError

    def parse_gosub(self, line_id: int) -> nodes.GoSubStmt:
        raise NotImplementedError

    def parse_return(self, line_id: int) -> nodes.ReturnStmt:
        raise NotImplementedError

    def parse_boolean_expression(self) -> nodes.BooleanExpr:
        raise NotImplementedError

    def parse_numeric_expression(self) -> nodes.NumericExpr:
        raise NotImplementedError

    def parse_term(self) -> nodes.NumericExpr:
        raise NotImplementedError

    def parse_factor(self) -> nodes.NumericExpr:
        raise NotImplementedError
