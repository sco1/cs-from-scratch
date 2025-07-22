from pathlib import Path

import pytest

from cs_from_scratch.NanoBASIC import errors
from cs_from_scratch.NanoBASIC.runtime import NanoBASICRuntime

EXAMPLES_ROOT = Path("./examples/NanoBASIC")

INTEGRATION_TEST_CASES = (
    (EXAMPLES_ROOT / "factorial.bas", "120"),
    (EXAMPLES_ROOT / "fib.bas", "0\n1\n1\n2\n3\n5\n8\n13\n21\n34\n55\n89"),
    (EXAMPLES_ROOT / "gcd.bas", "7"),
    (EXAMPLES_ROOT / "gosub.bas", "10"),
    (EXAMPLES_ROOT / "goto.bas", "Josh\nDave\nNanoBASIC ROCKS"),
    (EXAMPLES_ROOT / "if1.bas", "10\n40\n50\n60\n70\n100"),
    (EXAMPLES_ROOT / "if2.bas", "GOOD"),
    (EXAMPLES_ROOT / "print1.bas", "Hello World"),
    (EXAMPLES_ROOT / "print2.bas", "4\n12\n30\n7\n100\t9"),
    (EXAMPLES_ROOT / "print3.bas", "E is\t-31"),
    (EXAMPLES_ROOT / "variables.bas", "15"),
)


@pytest.mark.parametrize(("src", "truth_out"), INTEGRATION_TEST_CASES)
def test_nanobasic_integration(src: Path, truth_out: str, capsys: pytest.CaptureFixture) -> None:
    runtime = NanoBASICRuntime(src)
    runtime.execute()

    captured = capsys.readouterr()
    assert captured.out.strip() == truth_out


VAR_UNINIT_SRC = """\
10 PRINT A
"""


def test_uninitialized_var_raises(tmp_path: Path) -> None:
    src_filepath = tmp_path / "src.bas"
    src_filepath.write_text(VAR_UNINIT_SRC)

    runtime = NanoBASICRuntime(src_filepath)
    with pytest.raises(errors.InterpreterError, match="used before initialized"):
        runtime.execute()


GOTO_NO_LINE_SRC = """\
10 GOTO 20
"""


def test_goto_no_line_raises(tmp_path: Path) -> None:
    src_filepath = tmp_path / "src.bas"
    src_filepath.write_text(GOTO_NO_LINE_SRC)

    runtime = NanoBASICRuntime(src_filepath)
    with pytest.raises(errors.InterpreterError, match="No GOTO line ID"):
        runtime.execute()


GOSUB_NO_LINE_SRC = """\
10 GOSUB 20
"""


def test_gosub_no_line_raises(tmp_path: Path) -> None:
    src_filepath = tmp_path / "src.bas"
    src_filepath.write_text(GOSUB_NO_LINE_SRC)

    runtime = NanoBASICRuntime(src_filepath)
    with pytest.raises(errors.InterpreterError, match="No GOSUB line ID"):
        runtime.execute()


RETURN_NO_GOSUB_SRC = """\
10 RETURN
"""


def test_return_no_gosub_raises(tmp_path: Path) -> None:
    src_filepath = tmp_path / "src.bas"
    src_filepath.write_text(RETURN_NO_GOSUB_SRC)

    runtime = NanoBASICRuntime(src_filepath)
    with pytest.raises(errors.InterpreterError, match="RETURN without GOSUB"):
        runtime.execute()
