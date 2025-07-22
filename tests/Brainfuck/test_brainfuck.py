from pathlib import Path

import pytest

from cs_from_scratch.Brainfuck.brainfuck import (
    Brainfuck,
    InvalidLoopError,
    clamp_int,
    parse_brackets,
)

EXAMPLES_ROOT = Path("./examples/Brainfuck")

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


def test_naive_bracket_search_no_close_raises() -> None:
    bf = Brainfuck("[+++", cache_loops=False)
    with pytest.raises(InvalidLoopError):
        bf.find_bracket_match(0, forward=True)


MATCHED_BRACKETS_TEST_CASES = (
    (",>,[<.>-]", [(3, 8)]),
    ("[++[--]<<]", [(3, 6), (0, 9)]),
)


@pytest.mark.parametrize(("src", "truth_out"), MATCHED_BRACKETS_TEST_CASES)
def test_matched_bracket_search(src: str, truth_out: list[tuple[int, int]]) -> None:
    assert parse_brackets(src) == truth_out


def test_matched_bracket_no_open_raises() -> None:
    with pytest.raises(InvalidLoopError):
        _ = parse_brackets("+++]")


def test_cached_loop_no_close_raises() -> None:
    with pytest.raises(InvalidLoopError):
        _ = Brainfuck("[+++", cache_loops=True)


def test_hello_world_cached_bracket(capsys: pytest.CaptureFixture) -> None:
    bf = Brainfuck.from_file(EXAMPLES_ROOT / "hello_world_verbose.bf", cache_loops=True)
    bf.execute()

    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello World!"


def test_hello_world_naive_bracket(capsys: pytest.CaptureFixture) -> None:
    bf = Brainfuck.from_file(EXAMPLES_ROOT / "hello_world_verbose.bf", cache_loops=False)
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
