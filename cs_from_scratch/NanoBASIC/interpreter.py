import ast
from collections import deque

from cs_from_scratch.NanoBASIC import nodes
from cs_from_scratch.NanoBASIC.errors import InterpreterError
from cs_from_scratch.NanoBASIC.tokenizer import TokenType


class Interpreter:  # noqa: D101
    def __init__(self, statements: list[nodes.Statement]) -> None:
        self.statements = statements
        self.variable_table: dict[str, int] = {}
        self.statement_idx = 0
        self.subroutine_stack: deque[int] = deque()

    @property
    def current(self) -> nodes.Statement:  # noqa: D102
        return self.statements[self.statement_idx]

    def _find_line_idx(self, line_id: int) -> int | None:
        """
        Locate the statement index that corresponds to the query `line_id`.

        NOTE: It is assumed that the source file's leading line indices are in ascending order,
        therefore the parsed `Statement`s are also sorted.
        """
        # Binary search!
        low = 0
        high = len(self.statements) - 1
        while low <= high:
            mid = (low + high) // 2
            if self.statements[mid].line_id < line_id:
                low = mid + 1
            elif self.statements[mid].line_id > line_id:
                high = mid - 1
            else:
                return mid

        return None

    def _evaluate_numeric(self, numeric_expr: nodes.NumericExpr) -> int:
        match numeric_expr:
            case nodes.NumericLiteral(number=number):
                return number
            case nodes.VarRetrieve(name=name):
                if name in self.variable_table:
                    return self.variable_table[name]
                else:
                    raise InterpreterError(f"Var '{name}' used before initialized.", numeric_expr)
            case nodes.UnaryOp(operator=operator, expr=expr):
                if operator is TokenType.MINUS:
                    return -self._evaluate_numeric(expr)
                else:
                    raise InterpreterError(f"Expected '-' but got '{operator}'.", numeric_expr)
            case nodes.BinaryOp(operator=operator, left_expr=left, right_expr=right):
                match operator:
                    case TokenType.PLUS:
                        return self._evaluate_numeric(left) + self._evaluate_numeric(right)
                    case TokenType.MINUS:
                        return self._evaluate_numeric(left) - self._evaluate_numeric(right)
                    case TokenType.MULTIPLY:
                        return self._evaluate_numeric(left) * self._evaluate_numeric(right)
                    case TokenType.DIVIDE:
                        # NanoBASIC's only numeric type is integer, so use integer division
                        return self._evaluate_numeric(left) // self._evaluate_numeric(right)
                    case _:
                        raise InterpreterError(
                            f"Unexpected binary operator: '{operator}'.", numeric_expr
                        )
            case _:
                raise InterpreterError("Expected numeric expression.", numeric_expr)

    def _evaluate_boolean(self, boolean_expr: nodes.BooleanExpr) -> bool:
        left = self._evaluate_numeric(boolean_expr.left_expr)
        right = self._evaluate_numeric(boolean_expr.right_expr)

        match boolean_expr.operator:
            case TokenType.LESS:
                return left < right
            case TokenType.LESS_EQUAL:
                return left <= right
            case TokenType.GREATER:
                return left > right
            case TokenType.GREATER_EQUAL:
                return left >= right
            case TokenType.EQUAL:
                return left == right
            case TokenType.NOT_EQUAL:
                return left != right
            case _:
                raise InterpreterError(
                    f"Unexpected boolean operator: '{boolean_expr.operator}'.", boolean_expr
                )

    def _interpret(self, statement: nodes.Statement) -> None:
        match statement:
            case nodes.LetStmt(name=name, expr=expr):
                val = self._evaluate_numeric(expr)
                self.variable_table[name] = val

                self.statement_idx += 1
            case nodes.GoToStmt(line_expr=line_expr):
                goto_line_id = self._evaluate_numeric(line_expr)
                if (line_idx := self._find_line_idx(goto_line_id)) is not None:
                    self.statement_idx = line_idx
                else:
                    raise InterpreterError("No GOTO line ID.", self.current)
            case nodes.GoSubStmt(line_expr=line_expr):
                gosub_line_id = self._evaluate_numeric(line_expr)
                if (line_idx := self._find_line_idx(gosub_line_id)) is not None:
                    self.subroutine_stack.append(self.statement_idx + 1)  # Set for RETURN
                    self.statement_idx = line_idx
                else:
                    raise InterpreterError("No GOSUB line ID.", self.current)
            case nodes.ReturnStmt():
                if not self.subroutine_stack:
                    raise InterpreterError("RETURN without GOSUB.", self.current)

                self.statement_idx = self.subroutine_stack.pop()
            case nodes.PrintStmt(printables=printables):
                comps = []
                for p in printables:
                    if isinstance(p, nodes.NumericExpr):
                        comps.append(str(self._evaluate_numeric(p)))
                    else:  # printables should only be str or NumericExpr
                        # Probably not the best way to unescape any escaped quotes, but it works :)
                        unescaped = ast.literal_eval(f"'{p}'")
                        comps.append(unescaped)

                print("\t".join(comps))
                self.statement_idx += 1
            case nodes.IfStmt(boolean_expr=boolean_expr, then_stmt=then_stmt):
                if self._evaluate_boolean(boolean_expr):
                    self._interpret(then_stmt)
                else:
                    self.statement_idx += 1
            case _:
                raise InterpreterError(
                    f"Unexpected item: '{self.current}' in statement list.", self.current
                )

    def run(self) -> None:  # noqa: D102
        # Use a while loop rather than iterating over the statements since we have the ability to
        # jump around using GOTO and GOSUB
        while self.statement_idx < len(self.statements):
            self._interpret(self.current)
