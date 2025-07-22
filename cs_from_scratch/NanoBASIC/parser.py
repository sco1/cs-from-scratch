import typing as t

from cs_from_scratch.NanoBASIC import nodes
from cs_from_scratch.NanoBASIC.errors import ParserError
from cs_from_scratch.NanoBASIC.tokenizer import BOOLEAN_OPERATORS, Token, TokenType


class Parser:
    """The NanoBASIC recursive descent parser."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.token_idx = 0

    @property
    def exhausted(self) -> bool:  # noqa: D102
        return self.token_idx >= len(self.tokens)

    @property
    def previous(self) -> Token:  # noqa: D102
        return self.tokens[self.token_idx - 1]

    @property
    def current(self) -> Token:  # noqa: D102
        if self.exhausted:
            raise ParserError(f"No tokens after {self.previous.kind}", self.previous)

        return self.tokens[self.token_idx]

    def consume(self, kind: TokenType) -> Token:
        """
        Consume the next expected token & advance the token index.

        Raises a `ParserError` if the next token is not of the expected kind.
        """
        if self.current.kind is kind:
            self.token_idx += 1
            return self.previous

        raise ParserError(
            f"Expected {kind} after {self.previous} but got {self.current}", self.current
        )

    def parse(self) -> list[nodes.Statement]:
        """Begin the recursive descent parsing into a list of `Statement` nodes."""
        statements = []
        while not self.exhausted:
            statement = self.parse_line()
            statements.append(statement)

        return statements

    def parse_line(self) -> nodes.Statement:
        """
        Parse the current line and its component token(s).

        The leading line number is parsed & then further parsing is passed to the statement parser.
        """
        line_id = self.consume(TokenType.NUMBER)
        return self.parse_statement(t.cast(int, line_id.associated_value))

    def parse_statement(self, line_id: int) -> nodes.Statement:
        """Parse the line's remaining token(s) into a `Statement` node."""
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
        """
        Parse a NanoBASIC `PRINT` statement.

        A `PRINT` statement outputs any string literal or expression to the console; multiple
        comma-separated items can also be provided.

        For example:
            * `10 PRINT "Hello World"`
            * `10 PRINT 2 + 2`
            * `10 PRINT "2 plus 2 is", 2 + 2, "and 3 times 5 is", 3 * 5`

        NOTE: The leading line number is assumed to have been already consumed upstream & provided
        as an input to this method.
        """
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
        """
        Parse a NanoBASIC `IF` statment.

        An `IF` statement can only contain a single boolean expression & cannot have an else clause.
        If the condition is true, only a single statment, preceded by `THEN` is executed.

        For example:
            * `500 IF N < 10 THEN PRINT "Small Number"`
            * `700 IF V >= 34 THEN GOTO 20`

        NOTE: The leading line number is assumed to have been already consumed upstream & provided
        as an input to this method.
        """
        tok = self.consume(TokenType.IF_T)
        boolean_expr = self.parse_boolean_expression()
        self.consume(TokenType.THEN)
        stmt = self.parse_statement(line_id)

        return nodes.IfStmt(
            line_id=line_id,
            lineno=tok.lineno,
            col_start=tok.col_start,
            col_end=stmt.col_end,
            boolean_expr=boolean_expr,
            then_stmt=stmt,
        )

    def parse_let(self, line_id: int) -> nodes.LetStmt:
        """
        Parse a NanoBASIC `LET` statment.

        A `LET` statement binds a value to a variable. Identifiers can be of arbitrary length and
        composed of letters and underscores; all variables represent integers. The `LET` keyword
        must be followed by a variable name, an equal sign `=`, then a mathematical expression.

        For example:
            * `20 LET B = A`
            * `30 LET C = 23 - A`
            * `40 LET D = 5 * (24 + 25)`

        NOTE: The leading line number is assumed to have been already consumed upstream & provided
        as an input to this method.
        """
        tok = self.consume(TokenType.LET)
        var = self.consume(TokenType.VARIABLE)
        self.consume(TokenType.EQUAL)
        expr = self.parse_numeric_expression()

        return nodes.LetStmt(
            line_id=line_id,
            lineno=tok.lineno,
            col_start=tok.col_start,
            col_end=expr.col_end,
            name=t.cast(str, var.associated_value),
            expr=expr,
        )

    def parse_goto(self, line_id: int) -> nodes.GoToStmt:
        """
        Parse a NanoBASIC `GOTO` statment.

        A `GOTO` statement jumps to a line number with no way to return.

        For example:
            ```
            10 LET A = 5
            20 GOTO 40
            30 LET A = 10
            40 PRINT A
            REM Expect A to be 5
            ```

        NOTE: The leading line number is assumed to have been already consumed upstream & provided
        as an input to this method.
        """
        tok = self.consume(TokenType.GOTO)
        expr = self.parse_numeric_expression()

        return nodes.GoToStmt(
            line_id=line_id,
            lineno=tok.lineno,
            col_start=tok.col_start,
            col_end=expr.col_end,
            line_expr=expr,
        )

    def parse_gosub(self, line_id: int) -> nodes.GoSubStmt:
        """
        Parse a NanoBASIC `GOSUB` statment.

        A `GOSUB` statement jumps to a line number, but a matching `RETURN` statement will send the
        program back to the line just after the matching `GOSUB`.

        For example:
            ```
            10 GOTO 50
            20 LET A = 10
            40 RETURN
            50 LET A = 5
            60 GOSUB 20
            REM RETURN returns to here; we expect A to be 10
            70 PRINT A
            ```

        NOTE: The leading line number is assumed to have been already consumed upstream & provided
        as an input to this method.
        """
        tok = self.consume(TokenType.GOSUB)
        expr = self.parse_numeric_expression()

        return nodes.GoSubStmt(
            line_id=line_id,
            lineno=tok.lineno,
            col_start=tok.col_start,
            col_end=expr.col_end,
            line_expr=expr,
        )

    def parse_return(self, line_id: int) -> nodes.ReturnStmt:
        """
        Parse a NanoBASIC `RETURN` statment.

        A `RETURN` statement is utilized by `GOSUB` to send the program back to the line after the
        matching `GOSUB` call.

        NOTE: The leading line number is assumed to have been already consumed upstream & provided
        as an input to this method.
        """
        tok = self.consume(TokenType.RETURN_T)
        return nodes.ReturnStmt(
            line_id=line_id,
            lineno=tok.lineno,
            col_start=tok.col_start,
            col_end=tok.col_end,
        )

    def parse_boolean_expression(self) -> nodes.BooleanExpr:
        """
        Parse a NanoBASIC boolean expression.

        A boolean expression must contain two numeric expressions separated by a valid boolean
        operator, e.g. `2 > 2` or `3 >< 5`.
        """
        left = self.parse_numeric_expression()
        if self.current.kind in BOOLEAN_OPERATORS:
            operator = self.consume(self.current.kind)
            right = self.parse_numeric_expression()

            return nodes.BooleanExpr(
                lineno=left.lineno,
                col_start=left.col_start,
                col_end=right.col_end,
                operator=operator.kind,
                left_expr=left,
                right_expr=right,
            )

        raise ParserError(f"Boolean operator expected: found `{self.current.kind}`", self.current)

    def parse_numeric_expression(self) -> nodes.NumericExpr:
        """
        Parse a NanoBASIC numeric expression.

        Numeric expressions are defined by the grammar as: `<term> (('+'|'-') <term>)*`.
        """
        # As we descend, operators gain higher precedence; with addition/subtraction being lowest
        # precedence, if we have a binary operation we need to evaluate the terms' precedence first
        left = self.parse_term()
        while True:
            if self.exhausted:  # EOF
                return left

            if self.current.kind in {TokenType.PLUS, TokenType.MINUS}:
                operator = self.current.kind
                self.consume(operator)
                right = self.parse_term()

                left = nodes.BinaryOp(
                    lineno=left.lineno,
                    col_start=left.col_start,
                    col_end=right.col_end,
                    operator=operator,
                    left_expr=left,
                    right_expr=right,
                )
            else:  # End of expression
                break

        return left

    def parse_term(self) -> nodes.NumericExpr:
        """
        Parse a NanoBASIC term.

        Terms are defined by the grammar as: `<factor> (('*'|'/') <factor>)*`.
        """
        left = self.parse_factor()
        while True:
            if self.exhausted:  # EOF
                return left

            if self.current.kind in {TokenType.MULTIPLY, TokenType.DIVIDE}:
                operator = self.current.kind
                self.consume(operator)
                right = self.parse_factor()

                left = nodes.BinaryOp(
                    lineno=left.lineno,
                    col_start=left.col_start,
                    col_end=right.col_end,
                    operator=operator,
                    left_expr=left,
                    right_expr=right,
                )
            else:  # End of expression
                break

        return left

    def parse_factor(self) -> nodes.NumericExpr:
        """
        Parse a NanoBASIC factor.

        Factors are defined by the grammar as:
        `('-'|ε) <factor> | <var> | <number> | '('<expression>')'`.
        """
        match self.current.kind:
            case TokenType.VARIABLE:
                var = self.consume(TokenType.VARIABLE)
                return nodes.VarRetrieve(
                    lineno=var.lineno,
                    col_start=var.col_start,
                    col_end=var.col_end,
                    name=t.cast(str, var.associated_value),
                )
            case TokenType.NUMBER:
                num = self.consume(TokenType.NUMBER)
                return nodes.NumericLiteral(
                    lineno=num.lineno,
                    col_start=num.col_start,
                    col_end=num.col_end,
                    number=int(t.cast(str, num.associated_value)),
                )
            case TokenType.OPEN_PAREN:
                self.consume(TokenType.OPEN_PAREN)
                expr = self.parse_numeric_expression()

                if self.current.kind is not TokenType.CLOSE_PAREN:
                    raise ParserError("Expected matching close parernthesis.", self.current)

                self.consume(TokenType.CLOSE_PAREN)
                return expr
            case TokenType.MINUS:
                minus = self.consume(TokenType.MINUS)
                expr = self.parse_factor()

                return nodes.UnaryOp(
                    lineno=minus.lineno,
                    col_start=minus.col_start,
                    col_end=expr.col_end,
                    operator=TokenType.MINUS,
                    expr=expr,
                )
            case _:
                raise ParserError("Unexpected token in numeric expression.", self.current)
