from pathlib import Path

import pytest

from cs_from_scratch.NanoBASIC import errors
from cs_from_scratch.NanoBASIC.runtime import NanoBASICRuntime

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
