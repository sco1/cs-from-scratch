from dataclasses import dataclass

from cs_from_scratch.NanoBASIC.tokenizer import TokenType


@dataclass(frozen=True)
class Node:
    lineno: int
    col_start: int
    col_end: int


@dataclass(frozen=True)
class Statement(Node):
    line_id: int


@dataclass(frozen=True)
class NumericExpr(Node): ...


@dataclass(frozen=True)
class BinaryOp(NumericExpr):
    operator: TokenType
    left_expr: NumericExpr
    right_expr: NumericExpr

    def __repr__(self) -> str:
        return f"{self.left_expr} {self.operator} {self.right_expr}"


@dataclass(frozen=True)
class UnaryOp(NumericExpr):
    operator: TokenType
    expr: NumericExpr

    def __repr__(self) -> str:
        return f"{self.operator}{self.expr}"


@dataclass(frozen=True)
class NumericLiteral(NumericExpr):
    number: int


@dataclass(frozen=True)
class VarRetrieve(NumericExpr):
    name: str


@dataclass(frozen=True)
class BooleanExpr(Node):
    operator: TokenType
    left_expr: NumericExpr
    right_expr: NumericExpr

    def __repr__(self) -> str:
        return f"{self.left_expr} {self.operator} {self.right_expr}"


@dataclass(frozen=True)
class LetStmt(Statement):
    name: str
    expr: NumericExpr


@dataclass(frozen=True)
class GoToStmt(Statement):
    line_expr: NumericExpr


@dataclass(frozen=True)
class GoSubStmt(Statement):
    line_expr: NumericExpr


@dataclass(frozen=True)
class ReturnStmt(Statement): ...


@dataclass(frozen=True)
class PrintStmt(Statement):
    printables: list[str | NumericExpr]


@dataclass(frozen=True)
class IfStmt(Statement):
    boolean_expr: BooleanExpr
    then_stmt: Statement
