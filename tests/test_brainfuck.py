from pathlib import Path

import pytest

from cs_from_scratch.brainfuck import Brainfuck, InvalidJumpError, clamp_int

OVERFLOW_TEST_CASES = (
    (0, 0),
    (7, 7),
    (-1, 255),
    (256, 0),
)


@pytest.mark.parametrize(("num_in", "truth_out"), OVERFLOW_TEST_CASES)
def test_int_overflow(num_in: int, truth_out: int) -> None:
    assert clamp_int(num_in) == truth_out


BRACKET_SEARCH_TEST_CASES = (
    ("[++[--]<<]", 0, True, 9),
    ("[++[--]<<]", 9, False, 0),
    ("[++[--]<<]", 3, True, 6),
    ("[++[--]<<]", 6, False, 3),
)


@pytest.mark.parametrize(("src", "start", "forward", "truth_out"), BRACKET_SEARCH_TEST_CASES)
def test_bracket_search(src: str, start: int, forward: bool, truth_out: int) -> None:
    bf = Brainfuck(src)
    assert bf.find_bracket_match(start, forward=forward) == truth_out


def test_bracket_search_no_close_raises() -> None:
    bf = Brainfuck("[+++")
    with pytest.raises(InvalidJumpError):
        bf.find_bracket_match(0, forward=True)


EXAMPLES_ROOT = Path("./examples/brainfuck")


def test_hello_world(capsys: pytest.CaptureFixture) -> None:
    bf = Brainfuck.from_file(EXAMPLES_ROOT / "hello_world_verbose.bf")
    bf.execute()

    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello World!"


def test_fibonacci(capsys: pytest.CaptureFixture) -> None:
    bf = Brainfuck.from_file(EXAMPLES_ROOT / "fibonacci.bf")
    bf.execute()

    captured = capsys.readouterr()
    assert captured.out.strip() == "1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89"


def test_cell_size(capsys: pytest.CaptureFixture) -> None:
    bf = Brainfuck.from_file(EXAMPLES_ROOT / "cell_size.bf")
    bf.execute()

    captured = capsys.readouterr()
    assert captured.out.strip() == "8 bit cells"
