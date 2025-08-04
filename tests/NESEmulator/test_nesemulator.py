from pathlib import Path

import pytest

from cs_from_scratch.NESEmulator.cpu import CPU
from cs_from_scratch.NESEmulator.ppu import PPU
from cs_from_scratch.NESEmulator.rom import ROM
from tests.NESEmulator import TEST_ROM_BASE

NES_TEST_BASE = TEST_ROM_BASE / "nestest"


def test_nestest() -> None:
    TEST_ROM = NES_TEST_BASE / "nestest.nes"
    assert TEST_ROM.exists()
    TRUTH_LOG = NES_TEST_BASE / "nestest.log"
    assert TRUTH_LOG.exists()

    truth_log_lines = TRUTH_LOG.read_text().splitlines()

    rom = ROM(TEST_ROM)
    ppu = PPU(rom)
    cpu = CPU(ppu, rom)
    cpu.PC = 0xC000  # Special start location for tests

    log_line = 1
    while log_line < 5260:  # Run until first unofficial opcode test
        line = cpu.log()
        truth_line = truth_log_lines[log_line - 1]

        assert line[0:14] == truth_line[0:14], f"PC/Opcode mismatch at line {log_line}"
        assert line[48:73] == truth_line[48:73], f"Register mismatch at line {log_line}"

        cpu.step()
        log_line += 1


BLARGG_BASE = TEST_ROM_BASE / "instr_test-v5/rom_singles"
BLARGG_TEST_CASES = (
    (BLARGG_BASE / "01-basics.nes", "basics"),
    (BLARGG_BASE / "02-implied.nes", "implied"),
    (BLARGG_BASE / "10-branches.nes", "branches"),
    (BLARGG_BASE / "11-stack.nes", "stack"),
    (BLARGG_BASE / "12-jmp_jsr.nes", "jmp_jsr"),
    (BLARGG_BASE / "13-rts.nes", "rts"),
    (BLARGG_BASE / "14-rti.nes", "rti"),
    (BLARGG_BASE / "15-brk.nes", "brk"),
    (BLARGG_BASE / "16-special.nes", "special"),
)


@pytest.mark.parametrize(("rom_filepath", "test_shortname"), BLARGG_TEST_CASES)
def test_blargg(rom_filepath: Path, test_shortname: str) -> None:
    assert rom_filepath.exists()

    rom = ROM(rom_filepath)
    ppu = PPU(rom)
    cpu = CPU(ppu, rom)

    # Tests run as long as 0x6000 is 80, and then 0x6000 is result code; 0 means success
    rom.prg_ram[0] = 0x80
    while rom.prg_ram[0] == 0x80:  # Run until first unofficial opcode test
        cpu.step()

    msg = bytes(rom.prg_ram[4:]).decode("utf-8")
    print(msg[0 : msg.index("\0")])  # message ends with null terminator

    status = rom.prg_ram[0]
    assert status == 0, f"{test_shortname} test - Expected status 0, received {status}"
