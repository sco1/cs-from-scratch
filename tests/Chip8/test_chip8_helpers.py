import pytest

from cs_from_scratch.Chip8.vm import bcd, concat_nibbles

BCD_CASES = (
    (0, (0, 0, 0)),
    (1, (0, 0, 1)),
    (7, (0, 0, 7)),
    (10, (0, 1, 0)),
    (13, (0, 1, 3)),
    (42, (0, 4, 2)),
    (100, (1, 0, 0)),
    (101, (1, 0, 1)),
    (110, (1, 1, 0)),
    (111, (1, 1, 1)),
    (666, (6, 6, 6)),
)


@pytest.mark.parametrize(("in_num", "truth_out"), BCD_CASES)
def test_bcd(in_num: int, truth_out: tuple[int, int, int]) -> None:
    assert bcd(in_num) == truth_out


def test_bcd_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="must be in the range"):
        _ = bcd(1000)


def test_bcd_negative_input_raises() -> None:
    with pytest.raises(ValueError, match="must be in the range"):
        _ = bcd(-1)


CONCAT_NIBBLE_CASES = (
    ((0b0111, 0b1010), 0b01111010),
    ((0b1010, 0b1010), 0b10101010),
)


@pytest.mark.parametrize(("in_nibbles", "truth_out"), CONCAT_NIBBLE_CASES)
def test_concat_nibbles(in_nibbles: tuple[int, ...], truth_out: int) -> None:
    assert concat_nibbles(*in_nibbles) == truth_out
