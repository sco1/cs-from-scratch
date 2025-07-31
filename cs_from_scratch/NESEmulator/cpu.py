from __future__ import annotations

import typing as t
from array import array
from dataclasses import dataclass
from enum import IntEnum

from cs_from_scratch.NESEmulator.ppu import PPU, SPR_RAM_SIZE
from cs_from_scratch.NESEmulator.rom import ROM

STACK_POINTER_RESET = 0xFD  # CPU's stack pointer initially points here
STACK_START = 0x100  # Stack begins here in memory
RESET_VECTOR = 0xFFFC  # Contains address where program execution starts
NMI_VECTOR = 0xFFFA  # Address where program moves for NMI and vblank
IRQ_BRK_VECTOR = 0xFFFE  # Address where program moves to for IEQ intterupt
MEM_SIZE = 2048  # Size of NES RAM accessible by the CPU


class MemMode(IntEnum):
    DUMMY = 1
    ABSOLUTE = 2
    ABSOLUTE_X = 3
    ABSOLUTE_Y = 4
    ACCUMULATOR = 5
    IMMEDIATE = 6
    IMPLIED = 7
    INDEXED_INDIRECT = 8
    INDIRECT = 9
    INDIRECT_INDEXED = 10
    RELATIVE = 11
    ZEROPAGE = 12
    ZEROPAGE_X = 13
    ZEROPAGE_Y = 14


class InstructionType(IntEnum):
    ADC = 1
    AHX = 2
    ALR = 3
    ANC = 4
    AND = 5
    ARR = 6
    ASL = 7
    AXS = 8
    BCC = 9
    BCS = 10
    BEQ = 11
    BIT = 12
    BMI = 13
    BNE = 14
    BPL = 15
    BRK = 16
    BVC = 17
    BVS = 18
    CLC = 19
    CLD = 20
    CLI = 21
    CLV = 22
    CMP = 23
    CPX = 24
    CPY = 25
    DCP = 26
    DEC = 27
    DEX = 28
    DEY = 29
    EOR = 30
    INC = 31
    INX = 32
    INY = 33
    ISC = 34
    JMP = 35
    JSR = 36
    KIL = 37
    LAS = 38
    LAX = 39
    LDA = 40
    LDX = 41
    LDY = 42
    LSR = 43
    NOP = 44
    ORA = 45
    PHA = 46
    PHP = 47
    PLA = 48
    PLP = 49
    RLA = 50
    ROL = 51
    ROR = 52
    RRA = 53
    RTI = 54
    RTS = 55
    SAX = 56
    SBC = 57
    SEC = 58
    SED = 59
    SEI = 60
    SHX = 61
    SHY = 62
    SLO = 63
    SRE = 64
    STA = 65
    STX = 66
    STY = 67
    TAS = 68
    TAX = 69
    TAY = 70
    TSX = 71
    TXA = 72
    TXS = 73
    TYA = 74
    XAA = 75


BRANCH_INSTRUCTIONS = {
    InstructionType.BCC,
    InstructionType.BCS,
    InstructionType.BEQ,
    InstructionType.BMI,
    InstructionType.BNE,
    InstructionType.BPL,
    InstructionType.BVC,
    InstructionType.BVS,
}


@dataclass(frozen=True)
class Instruction:
    type: InstructionType
    method: t.Callable[[Instruction, int], None]
    mode: MemMode
    length: int
    ticks: int
    page_ticks: int


@dataclass
class Joypad:
    strobe: bool = False
    read_count: int = 0
    a: bool = False
    b: bool = False
    select: bool = False
    start: bool = False
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False


class CPU:
    def __init__(self, ppu: PPU, rom: ROM) -> None:
        # Connections to other console parts
        self.ppu = ppu
        self.rom = rom

        # CPU memory
        self.ram = array("B", [0] * MEM_SIZE)

        # Registers
        self.A = 0  # Accumulator
        self.X = 0  # Index
        self.Y = 0  # Index
        self.SP = STACK_POINTER_RESET  # Stack pointer
        self.PC = self._read_memory(RESET_VECTOR, MemMode.ABSOLUTE) | (
            self._read_memory(RESET_VECTOR + 1, MemMode.ABSOLUTE) << 8
        )  # Program counter

        # Flags
        self.C = False  # Carry
        self.Z = False  # Zero
        self.I = True  # Interrupt disable
        self.D = False  # Decimal mode
        self.B = False  # Break command
        self.V = False  # oVerflow
        self.N = False  # Negative

        # Misc State
        self.jumped = False
        self.page_crossed = False
        self.cpu_ticks = 0
        self.stall = 0  # Number of cycles to stall
        self.joypad1 = Joypad()

        # Jump instructions set in its own method to declutter
        self._set_instructions()

    def step(self) -> None:
        if self.stall > 0:
            self.stall -= 1
            self.cpu_ticks += 1
            return

        opcode = self._read_memory(self.PC, MemMode.ABSOLUTE)
        self.page_crossed = False
        self.jumped = False
        instruction = self.instructions[opcode]

        data = 0
        for i in range(1, instruction.length):
            data |= self._read_memory(self.PC + i, MemMode.ABSOLUTE) << ((i - 1) * 8)

        instruction.method(instruction, data)

        if not self.jumped:
            self.PC += instruction.length
        elif instruction.type in BRANCH_INSTRUCTIONS:
            # Branch instructions are +1 ticks if they succeed
            self.cpu_ticks += 1

        # Tick bookkeeping
        self.cpu_ticks += instruction.ticks
        if self.page_crossed:
            self.cpu_ticks += instruction.page_ticks

    def _address_for_mode(self, data: int, mode: MemMode) -> int:
        """Translate the data from an instruction to a memory address based on its mode."""

        def different_pages(addr1: int, addr2: int) -> bool:
            return (addr1 & 0xFF00) != (addr2 & 0xFF00)

        addr = 0
        match mode:
            case MemMode.ABSOLUTE:
                # Address is data
                addr = data
            case MemMode.ABSOLUTE_X:
                # X register is added to data to form the address
                addr = (data + self.X) & 0xFFFF
                self.page_crossed = different_pages(addr, addr - self.X)
            case MemMode.ABSOLUTE_Y:
                # Y register is added to data to form the address
                addr = (data + self.Y) & 0xFFFF
                self.page_crossed = different_pages(addr, addr - self.Y)
            case MemMode.INDEXED_INDIRECT:
                # 2-byte address is in RAM at data + X
                # 0xFF for zero-page wrapping
                ls = self.ram[(data + self.X) & 0xFF]
                ms = self.ram[(data + self.X + 1) & 0xFF]
                addr = (ms << 8) | ls
            case MemMode.INDIRECT:
                # 2-byte address is in RAM at data
                ls = self.ram[data]
                ms = self.ram[data + 1]
                if (data & 0xFF) == 0xFF:
                    ms = self.ram[data & 0xFF00]
                addr = (ms << 8) | ls
            case MemMode.INDIRECT_INDEXED:
                # The address at data in RAM is added to the Y register to form the address
                # 0xFF for zero-page wrapping
                ls = self.ram[data & 0xFF]
                ms = self.ram[(data + 1) & 0xFF]
                addr = (ms << 8) | ls
                addr = (addr + self.Y) & 0xFFFF
                self.page_crossed = different_pages(addr, addr - self.Y)
            case MemMode.RELATIVE:
                # data is added to PC to form the address
                # Signed integer
                if data < 0x80:
                    addr = (self.PC + 2 + data) & 0xFFFF
                else:
                    addr = (self.PC + 2 + (data - 256)) & 0xFFFF
            case MemMode.ZEROPAGE:
                # Similar to ABSOLUTE, but within the first 256 bytes of memory (zero page)
                addr = data
            case MemMode.ZEROPAGE_X:
                # Similar to ABSOLUTE_X, but within the first 256 bytes of memory (zero page)
                addr = (data + self.X) & 0xFF
            case MemMode.ZEROPAGE_Y:
                # Similar to ABSOLUTE_Y, but within the first 256 bytes of memory (zero page)
                addr = (data + self.Y) & 0xFF
            case _:
                # DUMMY is obviously ignored, ACCUMULATOR is handled by the individual instruction,
                # IMMEDIATE is not actually memory access & is handled by the individual
                # instruction, and IMPLIED is ???
                pass

        return addr

    def _read_memory(self, loc: int, mode: MemMode) -> int:
        if mode == MemMode.IMMEDIATE:
            return loc

        addr = self._address_for_mode(loc, mode)
        if addr < 0x2000:  # Main 2KB RAM goes up to 0x800
            return self.ram[addr % 0x800]  # Mirrors for the next 6 KB
        elif addr < 0x4000:  # 2000-2007 is PPU, mirrors every 8 bytes
            tmp = (addr % 8) | 0x2000  # get data from PPU register
            return self.ppu.read_register(tmp)
        elif addr == 0x4016:  # Joypad 1 status
            if self.joypad1.strobe:
                return self.joypad1.a

            self.joypad1.read_count += 1
            match self.joypad1.read_count:
                case 1:
                    return 0x40 | self.joypad1.a
                case 1:
                    return 0x40 | self.joypad1.b
                case 1:
                    return 0x40 | self.joypad1.select
                case 1:
                    return 0x40 | self.joypad1.start
                case 1:
                    return 0x40 | self.joypad1.up
                case 1:
                    return 0x40 | self.joypad1.down
                case 1:
                    return 0x40 | self.joypad1.left
                case 1:
                    return 0x40 | self.joypad1.right
                case _:
                    return 0x41
        elif addr < 0x6000:  # Other kinds of IO, not implemented here
            return 0
        else:  # Addresses from 0x6000 to 0xFFFF are from the cartridge
            return self.rom.read_cartridge(addr)

    def _write_memory(self, loc: int, mode: MemMode, val: int) -> None:
        if mode == MemMode.IMMEDIATE:
            self.ram[loc] = val
            return

        # See the memory map at: https://wiki.nesdev.org/w/index.php/CPU_memory_map
        addr = self._address_for_mode(loc, mode)
        if addr < 0x2000:  # Main 2KB RAM goes up to 0x800
            self.ram[addr % 0x800] = val  # Mirrors for next 6 KB
        elif addr < 0x3FFF:  # 2000-2007 is PPU, mirrors every 8 bytes
            tmp = (addr % 8) | 0x2000  # Write data to PPU register
            self.ppu.write_register(tmp, val)
        elif addr == 0x4014:  # DMA transfer of sprite data
            from_addr = val * 0x100  # Address to start copying from
            for i in range(SPR_RAM_SIZE):  # Copy all 256 bytes to sprite ram
                self.ppu.spr[i] = self._read_memory((from_addr + i), MemMode.ABSOLUTE)

            # Stall for 512 cycles while this completes
            self.stall = 512
        elif addr == 0x4016:  # Joypad 1
            if self.joypad1.strobe and (not bool(val & 1)):
                self.joypad1.read_count = 0
            self.joypad1.strobe = bool(val & 1)
            return
        elif addr < 0x6000:  # Other kinds of IO, not implemented here
            return
        else:  # Addresses from 0x6000 to 0xFFFF are from the cartridge
            return self.rom.write_cartridge(addr, val)

    def _setZN(self, val: int) -> None:
        self.Z = val == 0
        self.N = bool(val & 0x80) or (val < 0)

    def _stack_push(self, val: int) -> None:
        self.ram[(0x100 | self.SP)] = val
        self.SP = (self.SP - 1) & 0xFF

    def _stack_pop(self) -> int:
        self.SP = (self.SP + 1) & 0xFF
        return self.ram[(0x100 | self.SP)]

    @property
    def status(self) -> int:
        """
        Translate from our explicit CPU flags to a single 8-bit status.

        While our flags have been separated into individual attributes for convenience, the actual
        6502 has one 8-bit status register, where each flag is a single bit.

        See: https://www.nesdev.org/wiki/Status_flags for more info.
        """
        return (
            self.C
            | self.Z << 1
            | self.I << 2
            | self.D << 3
            | self.B << 4
            | 1 << 5
            | self.V << 6
            | self.N << 7
        )

    def _set_status(self, tmp: int) -> None:
        """
        Set status flag(s) based on the provided value.

        See: https://www.nesdev.org/wiki/Status_flags for more info.
        """
        self.C = bool(tmp & 0b00000001)
        self.Z = bool(tmp & 0b00000010)
        self.I = bool(tmp & 0b00000100)
        self.D = bool(tmp & 0b00001000)
        self.B = False
        self.V = bool(tmp & 0b01000000)
        self.N = bool(tmp & 0b10000000)

    def trigger_NMI(self) -> None:
        self._stack_push((self.PC >> 8) & 0xFF)
        self._stack_push(self.PC & 0xFF)

        # See: https://www.nesdev.org/wiki/Status_flags#The_B_flag
        self.B = True
        self._stack_push(self.status)
        self.B = False

        self.I = True
        # Set PC to NMI vector
        self.PC = (self._read_memory(NMI_VECTOR, MemMode.ABSOLUTE)) | (
            self._read_memory(NMI_VECTOR + 1, MemMode.ABSOLUTE) << 8
        )

    def log(self) -> str:
        """Dump debugging log."""
        opcode = self._read_memory(self.PC, MemMode.ABSOLUTE)
        instruction = self.instructions[opcode]

        if instruction.length < 2:
            data1 = " "
        else:
            data1 = f"{self._read_memory(self.PC + 1, MemMode.ABSOLUTE):02X}"

        if instruction.length < 3:
            data2 = " "
        else:
            data2 = f"{self._read_memory(self.PC + 2, MemMode.ABSOLUTE):02X}"

        return (
            f"{self.PC:04X}  {opcode:02X} {data1} {data2}  {instruction.type.name}{29 * ' '}"
            f"A:{self.A:02X} X:{self.X:02X} Y:{self.Y:02X} P:{self.status:02X} SP:{self.SP:02X}"
        )

    def _set_instructions(self) -> None:
        # This is a beast :)
        self.instructions = (
            Instruction(InstructionType.BRK, self._BRK, MemMode.IMPLIED, 1, 7, 0),  # 00
            Instruction(InstructionType.ORA, self._ORA, MemMode.INDEXED_INDIRECT, 2, 6, 0),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.SLO, self._noimpl, MemMode.INDEXED_INDIRECT, 0, 8, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ZEROPAGE, 2, 3, 0),  # 04
            Instruction(InstructionType.ORA, self._ORA, MemMode.ZEROPAGE, 2, 3, 0),  # 05
            Instruction(InstructionType.ASL, self._ASL, MemMode.ZEROPAGE, 2, 5, 0),  # 06
            Instruction(InstructionType.SLO, self._noimpl, MemMode.ZEROPAGE, 0, 5, 0),
            Instruction(InstructionType.PHP, self._PHP, MemMode.IMPLIED, 1, 3, 0),  # 08
            Instruction(InstructionType.ORA, self._ORA, MemMode.IMMEDIATE, 2, 2, 0),  # 09
            Instruction(InstructionType.ASL, self._ASL, MemMode.ACCUMULATOR, 1, 2, 0),  # 0a
            Instruction(InstructionType.ANC, self._noimpl, MemMode.IMMEDIATE, 0, 2, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ABSOLUTE, 3, 4, 0),  # 0c
            Instruction(InstructionType.ORA, self._ORA, MemMode.ABSOLUTE, 3, 4, 0),  # 0d
            Instruction(InstructionType.ASL, self._ASL, MemMode.ABSOLUTE, 3, 6, 0),  # 0e
            Instruction(InstructionType.SLO, self._noimpl, MemMode.ABSOLUTE, 0, 6, 0),
            Instruction(InstructionType.BPL, self._BPL, MemMode.RELATIVE, 2, 2, 1),  # 10
            Instruction(InstructionType.ORA, self._ORA, MemMode.INDIRECT_INDEXED, 2, 5, 1),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.SLO, self._noimpl, MemMode.INDIRECT_INDEXED, 0, 8, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ZEROPAGE_X, 2, 4, 0),  # 14
            Instruction(InstructionType.ORA, self._ORA, MemMode.ZEROPAGE_X, 2, 4, 0),  # 15
            Instruction(InstructionType.ASL, self._ASL, MemMode.ZEROPAGE_X, 2, 6, 0),  # 16
            Instruction(InstructionType.SLO, self._noimpl, MemMode.ZEROPAGE_X, 0, 6, 0),
            Instruction(InstructionType.CLC, self._CLC, MemMode.IMPLIED, 1, 2, 0),  # 18
            Instruction(InstructionType.ORA, self._ORA, MemMode.ABSOLUTE_Y, 3, 4, 1),  # 19
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMPLIED, 1, 2, 0),  # 1a
            Instruction(InstructionType.SLO, self._noimpl, MemMode.ABSOLUTE_Y, 0, 7, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ABSOLUTE_X, 3, 4, 1),  # 1c
            Instruction(InstructionType.ORA, self._ORA, MemMode.ABSOLUTE_X, 3, 4, 1),  # 1d
            Instruction(InstructionType.ASL, self._ASL, MemMode.ABSOLUTE_X, 3, 7, 0),  # 1e
            Instruction(InstructionType.SLO, self._noimpl, MemMode.ABSOLUTE_X, 0, 7, 0),
            Instruction(InstructionType.JSR, self._JSR, MemMode.ABSOLUTE, 3, 6, 0),  # 20
            Instruction(InstructionType.AND, self._AND, MemMode.INDEXED_INDIRECT, 2, 6, 0),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.RLA, self._noimpl, MemMode.INDEXED_INDIRECT, 0, 8, 0),
            Instruction(InstructionType.BIT, self._BIT, MemMode.ZEROPAGE, 2, 3, 0),  # 24
            Instruction(InstructionType.AND, self._AND, MemMode.ZEROPAGE, 2, 3, 0),  # 25
            Instruction(InstructionType.ROL, self._ROL, MemMode.ZEROPAGE, 2, 5, 0),  # 26
            Instruction(InstructionType.RLA, self._noimpl, MemMode.ZEROPAGE, 0, 5, 0),
            Instruction(InstructionType.PLP, self._PLP, MemMode.IMPLIED, 1, 4, 0),  # 28
            Instruction(InstructionType.AND, self._AND, MemMode.IMMEDIATE, 2, 2, 0),  # 29
            Instruction(InstructionType.ROL, self._ROL, MemMode.ACCUMULATOR, 1, 2, 0),  # 2a
            Instruction(InstructionType.ANC, self._noimpl, MemMode.IMMEDIATE, 0, 2, 0),
            Instruction(InstructionType.BIT, self._BIT, MemMode.ABSOLUTE, 3, 4, 0),  # 2c
            Instruction(InstructionType.AND, self._AND, MemMode.ABSOLUTE, 3, 4, 0),  # 2d
            Instruction(InstructionType.ROL, self._ROL, MemMode.ABSOLUTE, 3, 6, 0),  # 2e
            Instruction(InstructionType.RLA, self._noimpl, MemMode.ABSOLUTE, 0, 6, 0),
            Instruction(InstructionType.BMI, self._BMI, MemMode.RELATIVE, 2, 2, 1),  # 30
            Instruction(InstructionType.AND, self._AND, MemMode.INDIRECT_INDEXED, 2, 5, 1),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.RLA, self._noimpl, MemMode.INDIRECT_INDEXED, 0, 8, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ZEROPAGE_X, 2, 4, 0),  # 34
            Instruction(InstructionType.AND, self._AND, MemMode.ZEROPAGE_X, 2, 4, 0),  # 35
            Instruction(InstructionType.ROL, self._ROL, MemMode.ZEROPAGE_X, 2, 6, 0),  # 36
            Instruction(InstructionType.RLA, self._noimpl, MemMode.ZEROPAGE_X, 0, 6, 0),
            Instruction(InstructionType.SEC, self._SEC, MemMode.IMPLIED, 1, 2, 0),  # 38
            Instruction(InstructionType.AND, self._AND, MemMode.ABSOLUTE_Y, 3, 4, 1),  # 39
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMPLIED, 1, 2, 0),  # 3a
            Instruction(InstructionType.RLA, self._noimpl, MemMode.ABSOLUTE_Y, 0, 7, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ABSOLUTE_X, 3, 4, 1),  # 3c
            Instruction(InstructionType.AND, self._AND, MemMode.ABSOLUTE_X, 3, 4, 1),  # 3d
            Instruction(InstructionType.ROL, self._ROL, MemMode.ABSOLUTE_X, 3, 7, 0),  # 3e
            Instruction(InstructionType.RLA, self._noimpl, MemMode.ABSOLUTE_X, 0, 7, 0),
            Instruction(InstructionType.RTI, self._RTI, MemMode.IMPLIED, 1, 6, 0),  # 40
            Instruction(InstructionType.EOR, self._EOR, MemMode.INDEXED_INDIRECT, 2, 6, 0),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.SRE, self._noimpl, MemMode.INDEXED_INDIRECT, 0, 8, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ZEROPAGE, 2, 3, 0),  # 44
            Instruction(InstructionType.EOR, self._EOR, MemMode.ZEROPAGE, 2, 3, 0),  # 45
            Instruction(InstructionType.LSR, self._LSR, MemMode.ZEROPAGE, 2, 5, 0),  # 46
            Instruction(InstructionType.SRE, self._noimpl, MemMode.ZEROPAGE, 0, 5, 0),
            Instruction(InstructionType.PHA, self._PHA, MemMode.IMPLIED, 1, 3, 0),  # 48
            Instruction(InstructionType.EOR, self._EOR, MemMode.IMMEDIATE, 2, 2, 0),  # 49
            Instruction(InstructionType.LSR, self._LSR, MemMode.ACCUMULATOR, 1, 2, 0),
            Instruction(InstructionType.ALR, self._noimpl, MemMode.IMMEDIATE, 0, 2, 0),
            Instruction(InstructionType.JMP, self._JMP, MemMode.ABSOLUTE, 3, 3, 0),  # 4c
            Instruction(InstructionType.EOR, self._EOR, MemMode.ABSOLUTE, 3, 4, 0),  # 4d
            Instruction(InstructionType.LSR, self._LSR, MemMode.ABSOLUTE, 3, 6, 0),  # 4e
            Instruction(InstructionType.SRE, self._noimpl, MemMode.ABSOLUTE, 0, 6, 0),
            Instruction(InstructionType.BVC, self._BVC, MemMode.RELATIVE, 2, 2, 1),  # 50
            Instruction(InstructionType.EOR, self._EOR, MemMode.INDIRECT_INDEXED, 2, 5, 1),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.SRE, self._noimpl, MemMode.INDIRECT_INDEXED, 0, 8, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ZEROPAGE_X, 2, 4, 0),  # 54
            Instruction(InstructionType.EOR, self._EOR, MemMode.ZEROPAGE_X, 2, 4, 0),  # 55
            Instruction(InstructionType.LSR, self._LSR, MemMode.ZEROPAGE_X, 2, 6, 0),  # 56
            Instruction(InstructionType.SRE, self._noimpl, MemMode.ZEROPAGE_X, 0, 6, 0),
            Instruction(InstructionType.CLI, self._CLI, MemMode.IMPLIED, 1, 2, 0),  # 58
            Instruction(InstructionType.EOR, self._EOR, MemMode.ABSOLUTE_Y, 3, 4, 1),  # 59
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMPLIED, 1, 2, 0),  # 5a
            Instruction(InstructionType.SRE, self._noimpl, MemMode.ABSOLUTE_Y, 0, 7, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ABSOLUTE_X, 3, 4, 1),  # 5c
            Instruction(InstructionType.EOR, self._EOR, MemMode.ABSOLUTE_X, 3, 4, 1),  # 5d
            Instruction(InstructionType.LSR, self._LSR, MemMode.ABSOLUTE_X, 3, 7, 0),  # 5e
            Instruction(InstructionType.SRE, self._noimpl, MemMode.ABSOLUTE_X, 0, 7, 0),
            Instruction(InstructionType.RTS, self._RTS, MemMode.IMPLIED, 1, 6, 0),  # 60
            Instruction(InstructionType.ADC, self._ADC, MemMode.INDEXED_INDIRECT, 2, 6, 0),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.RRA, self._noimpl, MemMode.INDEXED_INDIRECT, 0, 8, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ZEROPAGE, 2, 3, 0),  # 64
            Instruction(InstructionType.ADC, self._ADC, MemMode.ZEROPAGE, 2, 3, 0),  # 65
            Instruction(InstructionType.ROR, self._ROR, MemMode.ZEROPAGE, 2, 5, 0),  # 66
            Instruction(InstructionType.RRA, self._noimpl, MemMode.ZEROPAGE, 0, 5, 0),
            Instruction(InstructionType.PLA, self._PLA, MemMode.IMPLIED, 1, 4, 0),  # 68
            Instruction(InstructionType.ADC, self._ADC, MemMode.IMMEDIATE, 2, 2, 0),  # 69
            Instruction(InstructionType.ROR, self._ROR, MemMode.ACCUMULATOR, 1, 2, 0),  # 6a
            Instruction(InstructionType.ARR, self._noimpl, MemMode.IMMEDIATE, 0, 2, 0),
            Instruction(InstructionType.JMP, self._JMP, MemMode.INDIRECT, 3, 5, 0),  # 6c
            Instruction(InstructionType.ADC, self._ADC, MemMode.ABSOLUTE, 3, 4, 0),  # 6d
            Instruction(InstructionType.ROR, self._ROR, MemMode.ABSOLUTE, 3, 6, 0),  # 6e
            Instruction(InstructionType.RRA, self._noimpl, MemMode.ABSOLUTE, 0, 6, 0),
            Instruction(InstructionType.BVS, self._BVS, MemMode.RELATIVE, 2, 2, 1),  # 70
            Instruction(InstructionType.ADC, self._ADC, MemMode.INDIRECT_INDEXED, 2, 5, 1),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.RRA, self._noimpl, MemMode.INDIRECT_INDEXED, 0, 8, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ZEROPAGE_X, 2, 4, 0),  # 74
            Instruction(InstructionType.ADC, self._ADC, MemMode.ZEROPAGE_X, 2, 4, 0),  # 75
            Instruction(InstructionType.ROR, self._ROR, MemMode.ZEROPAGE_X, 2, 6, 0),  # 76
            Instruction(InstructionType.RRA, self._noimpl, MemMode.ZEROPAGE_X, 0, 6, 0),
            Instruction(InstructionType.SEI, self._SEI, MemMode.IMPLIED, 1, 2, 0),  # 78
            Instruction(InstructionType.ADC, self._ADC, MemMode.ABSOLUTE_Y, 3, 4, 1),  # 79
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMPLIED, 1, 2, 0),  # 7a
            Instruction(InstructionType.RRA, self._noimpl, MemMode.ABSOLUTE_Y, 0, 7, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ABSOLUTE_X, 3, 4, 1),  # 7c
            Instruction(InstructionType.ADC, self._ADC, MemMode.ABSOLUTE_X, 3, 4, 1),  # 7d
            Instruction(InstructionType.ROR, self._ROR, MemMode.ABSOLUTE_X, 3, 7, 0),  # 7e
            Instruction(InstructionType.RRA, self._noimpl, MemMode.ABSOLUTE_X, 0, 7, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMMEDIATE, 2, 2, 0),  # 80
            Instruction(InstructionType.STA, self._STA, MemMode.INDEXED_INDIRECT, 2, 6, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMMEDIATE, 0, 2, 0),  # 82
            Instruction(InstructionType.SAX, self._noimpl, MemMode.INDEXED_INDIRECT, 0, 6, 0),
            Instruction(InstructionType.STY, self._STY, MemMode.ZEROPAGE, 2, 3, 0),  # 84
            Instruction(InstructionType.STA, self._STA, MemMode.ZEROPAGE, 2, 3, 0),  # 85
            Instruction(InstructionType.STX, self._STX, MemMode.ZEROPAGE, 2, 3, 0),  # 86
            Instruction(InstructionType.SAX, self._noimpl, MemMode.ZEROPAGE, 0, 3, 0),
            Instruction(InstructionType.DEY, self._DEY, MemMode.IMPLIED, 1, 2, 0),  # 88
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMMEDIATE, 0, 2, 0),  # 89
            Instruction(InstructionType.TXA, self._TXA, MemMode.IMPLIED, 1, 2, 0),  # 8a
            Instruction(InstructionType.XAA, self._noimpl, MemMode.IMMEDIATE, 0, 2, 0),
            Instruction(InstructionType.STY, self._STY, MemMode.ABSOLUTE, 3, 4, 0),  # 8c
            Instruction(InstructionType.STA, self._STA, MemMode.ABSOLUTE, 3, 4, 0),  # 8d
            Instruction(InstructionType.STX, self._STX, MemMode.ABSOLUTE, 3, 4, 0),  # 8e
            Instruction(InstructionType.SAX, self._noimpl, MemMode.ABSOLUTE, 0, 4, 0),
            Instruction(InstructionType.BCC, self._BCC, MemMode.RELATIVE, 2, 2, 1),  # 90
            Instruction(InstructionType.STA, self._STA, MemMode.INDIRECT_INDEXED, 2, 6, 0),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.AHX, self._noimpl, MemMode.INDIRECT_INDEXED, 0, 6, 0),
            Instruction(InstructionType.STY, self._STY, MemMode.ZEROPAGE_X, 2, 4, 0),  # 94
            Instruction(InstructionType.STA, self._STA, MemMode.ZEROPAGE_X, 2, 4, 0),  # 95
            Instruction(InstructionType.STX, self._STX, MemMode.ZEROPAGE_Y, 2, 4, 0),  # 96
            Instruction(InstructionType.SAX, self._noimpl, MemMode.ZEROPAGE_Y, 0, 4, 0),
            Instruction(InstructionType.TYA, self._TYA, MemMode.IMPLIED, 1, 2, 0),  # 98
            Instruction(InstructionType.STA, self._STA, MemMode.ABSOLUTE_Y, 3, 5, 0),  # 99
            Instruction(InstructionType.TXS, self._TXS, MemMode.IMPLIED, 1, 2, 0),  # 9a
            Instruction(InstructionType.TAS, self._noimpl, MemMode.ABSOLUTE_Y, 0, 5, 0),
            Instruction(InstructionType.SHY, self._noimpl, MemMode.ABSOLUTE_X, 0, 5, 0),
            Instruction(InstructionType.STA, self._STA, MemMode.ABSOLUTE_X, 3, 5, 0),  # 9d
            Instruction(InstructionType.SHX, self._noimpl, MemMode.ABSOLUTE_Y, 0, 5, 0),
            Instruction(InstructionType.AHX, self._noimpl, MemMode.ABSOLUTE_Y, 0, 5, 0),
            Instruction(InstructionType.LDY, self._LDY, MemMode.IMMEDIATE, 2, 2, 0),  # a0
            Instruction(InstructionType.LDA, self._LDA, MemMode.INDEXED_INDIRECT, 2, 6, 0),
            Instruction(InstructionType.LDX, self._LDX, MemMode.IMMEDIATE, 2, 2, 0),  # a2
            Instruction(InstructionType.LAX, self._noimpl, MemMode.INDEXED_INDIRECT, 0, 6, 0),
            Instruction(InstructionType.LDY, self._LDY, MemMode.ZEROPAGE, 2, 3, 0),  # a4
            Instruction(InstructionType.LDA, self._LDA, MemMode.ZEROPAGE, 2, 3, 0),  # a5
            Instruction(InstructionType.LDX, self._LDX, MemMode.ZEROPAGE, 2, 3, 0),  # a6
            Instruction(InstructionType.LAX, self._noimpl, MemMode.ZEROPAGE, 0, 3, 0),
            Instruction(InstructionType.TAY, self._TAY, MemMode.IMPLIED, 1, 2, 0),  # a8
            Instruction(InstructionType.LDA, self._LDA, MemMode.IMMEDIATE, 2, 2, 0),  # a9
            Instruction(InstructionType.TAX, self._TAX, MemMode.IMPLIED, 1, 2, 0),  # aa
            Instruction(InstructionType.LAX, self._noimpl, MemMode.IMMEDIATE, 0, 2, 0),
            Instruction(InstructionType.LDY, self._LDY, MemMode.ABSOLUTE, 3, 4, 0),  # ac
            Instruction(InstructionType.LDA, self._LDA, MemMode.ABSOLUTE, 3, 4, 0),  # ad
            Instruction(InstructionType.LDX, self._LDX, MemMode.ABSOLUTE, 3, 4, 0),  # ae
            Instruction(InstructionType.LAX, self._noimpl, MemMode.ABSOLUTE, 0, 4, 0),
            Instruction(InstructionType.BCS, self._BCS, MemMode.RELATIVE, 2, 2, 1),  # b0
            Instruction(InstructionType.LDA, self._LDA, MemMode.INDIRECT_INDEXED, 2, 5, 1),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.LAX, self._noimpl, MemMode.INDIRECT_INDEXED, 0, 5, 1),
            Instruction(InstructionType.LDY, self._LDY, MemMode.ZEROPAGE_X, 2, 4, 0),  # b4
            Instruction(InstructionType.LDA, self._LDA, MemMode.ZEROPAGE_X, 2, 4, 0),  # b5
            Instruction(InstructionType.LDX, self._LDX, MemMode.ZEROPAGE_Y, 2, 4, 0),  # b6
            Instruction(InstructionType.LAX, self._noimpl, MemMode.ZEROPAGE_Y, 0, 4, 0),
            Instruction(InstructionType.CLV, self._CLV, MemMode.IMPLIED, 1, 2, 0),  # b8
            Instruction(InstructionType.LDA, self._LDA, MemMode.ABSOLUTE_Y, 3, 4, 1),  # b9
            Instruction(InstructionType.TSX, self._TSX, MemMode.IMPLIED, 1, 2, 0),  # ba
            Instruction(InstructionType.LAS, self._noimpl, MemMode.ABSOLUTE_Y, 0, 4, 1),
            Instruction(InstructionType.LDY, self._LDY, MemMode.ABSOLUTE_X, 3, 4, 1),  # bc
            Instruction(InstructionType.LDA, self._LDA, MemMode.ABSOLUTE_X, 3, 4, 1),  # bd
            Instruction(InstructionType.LDX, self._LDX, MemMode.ABSOLUTE_Y, 3, 4, 1),  # be
            Instruction(InstructionType.LAX, self._noimpl, MemMode.ABSOLUTE_Y, 0, 4, 1),
            Instruction(InstructionType.CPY, self._CPY, MemMode.IMMEDIATE, 2, 2, 0),  # c0
            Instruction(InstructionType.CMP, self._CMP, MemMode.INDEXED_INDIRECT, 2, 6, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMMEDIATE, 0, 2, 0),  # c2
            Instruction(InstructionType.DCP, self._noimpl, MemMode.INDEXED_INDIRECT, 0, 8, 0),
            Instruction(InstructionType.CPY, self._CPY, MemMode.ZEROPAGE, 2, 3, 0),  # c4
            Instruction(InstructionType.CMP, self._CMP, MemMode.ZEROPAGE, 2, 3, 0),  # c5
            Instruction(InstructionType.DEC, self._DEC, MemMode.ZEROPAGE, 2, 5, 0),  # c6
            Instruction(InstructionType.DCP, self._noimpl, MemMode.ZEROPAGE, 0, 5, 0),
            Instruction(InstructionType.INY, self._INY, MemMode.IMPLIED, 1, 2, 0),  # c8
            Instruction(InstructionType.CMP, self._CMP, MemMode.IMMEDIATE, 2, 2, 0),  # c9
            Instruction(InstructionType.DEX, self._DEX, MemMode.IMPLIED, 1, 2, 0),  # ca
            Instruction(InstructionType.AXS, self._noimpl, MemMode.IMMEDIATE, 0, 2, 0),
            Instruction(InstructionType.CPY, self._CPY, MemMode.ABSOLUTE, 3, 4, 0),  # cc
            Instruction(InstructionType.CMP, self._CMP, MemMode.ABSOLUTE, 3, 4, 0),  # cd
            Instruction(InstructionType.DEC, self._DEC, MemMode.ABSOLUTE, 3, 6, 0),  # ce
            Instruction(InstructionType.DCP, self._noimpl, MemMode.ABSOLUTE, 0, 6, 0),
            Instruction(InstructionType.BNE, self._BNE, MemMode.RELATIVE, 2, 2, 1),  # d0
            Instruction(InstructionType.CMP, self._CMP, MemMode.INDIRECT_INDEXED, 2, 5, 1),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.DCP, self._noimpl, MemMode.INDIRECT_INDEXED, 0, 8, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ZEROPAGE_X, 2, 4, 0),  # d4
            Instruction(InstructionType.CMP, self._CMP, MemMode.ZEROPAGE_X, 2, 4, 0),  # d5
            Instruction(InstructionType.DEC, self._DEC, MemMode.ZEROPAGE_X, 2, 6, 0),  # d6
            Instruction(InstructionType.DCP, self._noimpl, MemMode.ZEROPAGE_X, 0, 6, 0),
            Instruction(InstructionType.CLD, self._CLD, MemMode.IMPLIED, 1, 2, 0),  # d8
            Instruction(InstructionType.CMP, self._CMP, MemMode.ABSOLUTE_Y, 3, 4, 1),  # d9
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMPLIED, 1, 2, 0),  # da
            Instruction(InstructionType.DCP, self._noimpl, MemMode.ABSOLUTE_Y, 0, 7, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ABSOLUTE_X, 3, 4, 1),  # dc
            Instruction(InstructionType.CMP, self._CMP, MemMode.ABSOLUTE_X, 3, 4, 1),  # dd
            Instruction(InstructionType.DEC, self._DEC, MemMode.ABSOLUTE_X, 3, 7, 0),  # de
            Instruction(InstructionType.DCP, self._noimpl, MemMode.ABSOLUTE_X, 0, 7, 0),
            Instruction(InstructionType.CPX, self._CPX, MemMode.IMMEDIATE, 2, 2, 0),  # e0
            Instruction(InstructionType.SBC, self._SBC, MemMode.INDEXED_INDIRECT, 2, 6, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMMEDIATE, 0, 2, 0),  # e2
            Instruction(InstructionType.ISC, self._noimpl, MemMode.INDEXED_INDIRECT, 0, 8, 0),
            Instruction(InstructionType.CPX, self._CPX, MemMode.ZEROPAGE, 2, 3, 0),  # e4
            Instruction(InstructionType.SBC, self._SBC, MemMode.ZEROPAGE, 2, 3, 0),  # e5
            Instruction(InstructionType.INC, self._INC, MemMode.ZEROPAGE, 2, 5, 0),  # e6
            Instruction(InstructionType.ISC, self._noimpl, MemMode.ZEROPAGE, 0, 5, 0),
            Instruction(InstructionType.INX, self._INX, MemMode.IMPLIED, 1, 2, 0),  # e8
            Instruction(InstructionType.SBC, self._SBC, MemMode.IMMEDIATE, 2, 2, 0),  # e9
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMPLIED, 1, 2, 0),  # ea
            Instruction(InstructionType.SBC, self._SBC, MemMode.IMMEDIATE, 0, 2, 0),  # eb
            Instruction(InstructionType.CPX, self._CPX, MemMode.ABSOLUTE, 3, 4, 0),  # ec
            Instruction(InstructionType.SBC, self._SBC, MemMode.ABSOLUTE, 3, 4, 0),  # ed
            Instruction(InstructionType.INC, self._INC, MemMode.ABSOLUTE, 3, 6, 0),  # ee
            Instruction(InstructionType.ISC, self._noimpl, MemMode.ABSOLUTE, 0, 6, 0),
            Instruction(InstructionType.BEQ, self._BEQ, MemMode.RELATIVE, 2, 2, 1),  # f0
            Instruction(InstructionType.SBC, self._SBC, MemMode.INDIRECT_INDEXED, 2, 5, 1),
            Instruction(InstructionType.KIL, self._noimpl, MemMode.IMPLIED, 0, 2, 0),
            Instruction(InstructionType.ISC, self._noimpl, MemMode.INDIRECT_INDEXED, 0, 8, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ZEROPAGE_X, 2, 4, 0),  # f4
            Instruction(InstructionType.SBC, self._SBC, MemMode.ZEROPAGE_X, 2, 4, 0),  # f5
            Instruction(InstructionType.INC, self._INC, MemMode.ZEROPAGE_X, 2, 6, 0),  # f6
            Instruction(InstructionType.ISC, self._noimpl, MemMode.ZEROPAGE_X, 0, 6, 0),
            Instruction(InstructionType.SED, self._SED, MemMode.IMPLIED, 1, 2, 0),  # f8
            Instruction(InstructionType.SBC, self._SBC, MemMode.ABSOLUTE_Y, 3, 4, 1),  # f9
            Instruction(InstructionType.NOP, self._NOP, MemMode.IMPLIED, 1, 2, 0),  # fa
            Instruction(InstructionType.ISC, self._noimpl, MemMode.ABSOLUTE_Y, 0, 7, 0),
            Instruction(InstructionType.NOP, self._NOP, MemMode.ABSOLUTE_X, 3, 4, 1),  # fc
            Instruction(InstructionType.SBC, self._SBC, MemMode.ABSOLUTE_X, 3, 4, 1),  # fd
            Instruction(InstructionType.INC, self._INC, MemMode.ABSOLUTE_X, 3, 7, 0),  # fe
            Instruction(InstructionType.ISC, self._noimpl, MemMode.ABSOLUTE_X, 0, 7, 0),
        )

    def _ADC(self, instruction: Instruction, data: int) -> None:
        """Add memory to accumulator with carry."""
        src = self._read_memory(data, instruction.mode)

        signed_result = src + self.A + self.C

        self.V = bool(~(self.A ^ src) & (self.A ^ signed_result) & 0x80)
        # Since the registers are just 8 bits, we can just do the arithmetic with Python's regular
        # integers and then just mod off anything above 255
        self.A = (self.A + src + self.C) % 256
        self.C = signed_result > 0xFF
        self._setZN(self.A)

    def _AND(self, instruction: Instruction, data: int) -> None:
        """Bitwise AND with accumulator."""
        src = self._read_memory(data, instruction.mode)

        self.A = self.A & src
        self._setZN(self.A)

    def _ASL(self, instruction: Instruction, data: int) -> None:
        """Arithmetic shift left."""
        if instruction.mode == MemMode.ACCUMULATOR:
            src = self.A
        else:
            src = self._read_memory(data, instruction.mode)

        self.C = bool(src >> 7)  # Carry is set to the 7th bit
        src = (src << 1) & 0xFF
        self._setZN(src)

        if instruction.mode == MemMode.ACCUMULATOR:
            self.A = src
        else:
            self._write_memory(data, instruction.mode, src)

    def _BCC(self, instruction: Instruction, data: int) -> None:
        """Branch if carry clear."""
        if not self.C:
            self.PC = self._address_for_mode(data, instruction.mode)
            self.jumped = True

    def _BCS(self, instruction: Instruction, data: int) -> None:
        """Branch if carry clear."""
        if not self.C:
            self.PC = self._address_for_mode(data, instruction.mode)
            self.jumped = True

    def _BEQ(self, instruction: Instruction, data: int) -> None:
        """Branch on result zero."""
        if self.Z:
            self.pc = self._address_for_mode(data, instruction.mode)
            self.jumped = True

    def _BIT(self, instruction: Instruction, data: int) -> None:
        """Bit tests in memory with accumulator."""
        src = self._read_memory(data, instruction.mode)

        self.V = bool((src >> 6) & 1)
        self.Z = (src & self.A) == 0
        self.N = (src >> 7) == 1

    def _BMI(self, instruction: Instruction, data: int) -> None:
        """Branch on result minus."""
        if self.N:
            self.PC = self._address_for_mode(data, instruction.mode)
            self.jumped = True

    def _BNE(self, instruction: Instruction, data: int) -> None:
        """Branch on result not zero."""
        if not self.Z:
            self.PC = self._address_for_mode(data, instruction.mode)
            self.jumped = True

    def _BPL(self, instruction: Instruction, data: int) -> None:
        """Branch on result plus."""
        if not self.N:
            self.PC = self._address_for_mode(data, instruction.mode)
            self.jumped = True

    def _BRK(self, instruction: Instruction, data: int) -> None:
        """Force break."""
        self.PC += 2

        # Push PC to stack
        self._stack_push((self.PC >> 8) & 0xFF)
        self._stack_push(self.PC & 0xFF)

        # Push status to stack
        self.B = True
        self._stack_push(self.status)
        self.B = False
        self.I = True

        # Set PC to reset vector
        self.PC = (self._read_memory(IRQ_BRK_VECTOR, MemMode.ABSOLUTE)) | (
            self._read_memory(IRQ_BRK_VECTOR + 1, MemMode.ABSOLUTE) << 8
        )
        self.jumped = True

    def _BVC(self, instruction: Instruction, data: int) -> None:
        """Branch on overflow clear."""
        if not self.V:
            self.PC = self._address_for_mode(data, instruction.mode)
            self.jumped = True

    def _BVS(self, instruction: Instruction, data: int) -> None:
        """Branch on overflow set."""
        if self.V:
            self.PC = self._address_for_mode(data, instruction.mode)
            self.jumped = True

    def _CLC(self, instruction: Instruction, data: int) -> None:
        """Clear carry."""
        self.C = False

    def _CLD(self, instruction: Instruction, data: int) -> None:
        """Clear decimal."""
        self.D = False

    def _CLI(self, instruction: Instruction, data: int) -> None:
        """Clear interrupt."""
        self.I = False

    def _CLV(self, instruction: Instruction, data: int) -> None:
        """Clear overflow."""
        self.V = False

    def _CMP(self, instruction: Instruction, data: int) -> None:
        """Compare accumulator."""
        src = self._read_memory(data, instruction.mode)

        self.C = self.A >= src
        self._setZN(self.A - src)

    def _CPX(self, instruction: Instruction, data: int) -> None:
        """Compare X register."""
        src = self._read_memory(data, instruction.mode)

        self.C = self.X >= src
        self._setZN(self.X - src)

    def _CPY(self, instruction: Instruction, data: int) -> None:
        """Compare Y register."""
        src = self._read_memory(data, instruction.mode)

        self.C = self.Y >= src
        self._setZN(self.Y - src)

    def _DEC(self, instruction: Instruction, data: int) -> None:
        """Decrement memory."""
        src = self._read_memory(data, instruction.mode)

        src = (src - 1) & 0xFF
        self._write_memory(data, instruction.mode, src)
        self._setZN(src)

    def _DEX(self, instruction: Instruction, data: int) -> None:
        """Decrement X."""
        self.X = (self.X - 1) & 0xFF
        self._setZN(self.X)

    def _DEY(self, instruction: Instruction, data: int) -> None:
        """Decrement Y."""
        self.Y = (self.Y - 1) & 0xFF
        self._setZN(self.Y)

    def _EOR(self, instruction: Instruction, data: int) -> None:
        """Exclusive or memory with accumulator."""
        self.A ^= self._read_memory(data, instruction.mode)
        self._setZN(self.A)

    def _INC(self, instruction: Instruction, data: int) -> None:
        """Increment memory."""
        src = self._read_memory(data, instruction.mode)
        src = (src + 1) & 0xFF

        self._write_memory(data, instruction.mode, src)
        self._setZN(src)

    def _INX(self, instruction: Instruction, data: int) -> None:
        """Increment X."""
        self.X = (self.X + 1) & 0xFF
        self._setZN(self.X)

    def _INY(self, instruction: Instruction, data: int) -> None:
        """Increment Y."""
        self.Y = (self.Y + 1) & 0xFF
        self._setZN(self.Y)

    def _JMP(self, instruction: Instruction, data: int) -> None:
        """Jump!"""
        self.PC = self._address_for_mode(data, instruction.mode)
        self.jumped = True

    def _JSR(self, instruction: Instruction, data: int) -> None:
        """Jump to subroutine."""
        self.PC += 2

        # Push PC to stack
        self._stack_push((self.PC >> 8) & 0xFF)
        self._stack_push(self.PC & 0xFF)

        # Jump to subroutine
        self.PC = self._address_for_mode(data, instruction.mode)
        self.jumped = True

    def _LDA(self, instruction: Instruction, data: int) -> None:
        """Load accumulator with memory."""
        self.A = self._read_memory(data, instruction.mode)
        self._setZN(self.A)

    def _LDX(self, instruction: Instruction, data: int) -> None:
        """Load X with memory."""
        self.X = self._read_memory(data, instruction.mode)
        self._setZN(self.X)

    def _LDY(self, instruction: Instruction, data: int) -> None:
        """Load Y with memory."""
        self.Y = self._read_memory(data, instruction.mode)
        self._setZN(self.Y)

    def _LSR(self, instruction: Instruction, data: int) -> None:
        """Logical shift right."""
        if instruction.mode == MemMode.ACCUMULATOR:
            src = self.A
        else:
            src = self._read_memory(data, instruction.mode)

        self.C = bool(src & 1)  # carry is set to 0th bit

        src >>= 1
        self._setZN(src)

        if instruction.mode == MemMode.ACCUMULATOR:
            self.A = src
        else:
            self._write_memory(data, instruction.mode, src)

    def _NOP(self, instruction: Instruction, data: int) -> None:
        """No op."""
        pass

    def _ORA(self, instruction: Instruction, data: int) -> None:
        """OR memory with accumulator."""
        self.A |= self._read_memory(data, instruction.mode)
        self._setZN(self.A)

    def _PHA(self, instruction: Instruction, data: int) -> None:
        """Push accumulator."""
        self._stack_push(self.A)

    def _PHP(self, instruction: Instruction, data: int) -> None:
        """Push status."""
        # See: https://www.nesdev.org/wiki/Status_flags#The_B_flag
        self.B = True
        self._stack_push(self.status)
        self.B = False

    def _PLA(self, instruction: Instruction, data: int) -> None:
        """Pull accumulator."""
        self.A = self._stack_pop()
        self._setZN(self.A)

    def _PLP(self, instruction: Instruction, data: int) -> None:
        """Pull status."""
        self._set_status(self._stack_pop())

    def _ROL(self, instruction: Instruction, data: int) -> None:
        """Rotate one bit left."""
        if instruction.mode == MemMode.ACCUMULATOR:
            src = self.A
        else:
            src = self._read_memory(data, instruction.mode)

        old_c = self.C
        self.C = bool((src >> 7) & 1)  # carry is set to 7th bit

        src = ((src << 1) | old_c) & 0xFF
        self._setZN(src)

        if instruction.mode == MemMode.ACCUMULATOR:
            self.A = src
        else:
            self._write_memory(data, instruction.mode, src)

    def _ROR(self, instruction: Instruction, data: int) -> None:
        """Rotate one bit right."""
        if instruction.mode == MemMode.ACCUMULATOR:
            src = self.A
        else:
            src = self._read_memory(data, instruction.mode)

        old_c = self.C
        self.C = bool(src & 1)  # carry is set to 0th bit

        src = ((src >> 1) | (old_c << 7)) & 0xFF
        self._setZN(src)

        if instruction.mode == MemMode.ACCUMULATOR:
            self.A = src
        else:
            self._write_memory(data, instruction.mode, src)

    def _RTI(self, instruction: Instruction, data: int) -> None:
        """Return from interrupt."""
        # Pull status out
        self._set_status(self._stack_pop())

        # Pull PC out
        lb = self._stack_pop()
        hb = self._stack_pop()
        self.PC = (hb << 8) | lb
        self.jumped = True

    def _RTS(self, instruction: Instruction, data: int) -> None:
        """Return from subroutine."""
        # Pull PC out
        lb = self._stack_pop()
        hb = self._stack_pop()
        self.PC = ((hb << 8) | lb) + 1  # 1 past last instruction
        self.jumped = True

    def _SBC(self, instruction: Instruction, data: int) -> None:
        """Subtract with carry."""
        src = self._read_memory(data, instruction.mode)

        signed_result = self.A - src - (1 - self.C)

        # Set overflow
        self.V = bool((self.A ^ src) & (self.A ^ signed_result) & 0x80)
        # Since the registers are just 8 bits, we can just do the arithmetic with Python's regular
        # integers and then just mod off anything above 255
        self.A = (self.A - src - (1 - self.C)) % 256
        self.C = not (signed_result < 0)  # set carry

        self._setZN(self.A)

    def _SEC(self, instruction: Instruction, data: int) -> None:
        """Set carry."""
        self.C = True

    def _SED(self, instruction: Instruction, data: int) -> None:
        """Set decimal."""
        self.D = True

    def _SEI(self, instruction: Instruction, data: int) -> None:
        """Set interrupt."""
        self.I = True

    def _STA(self, instruction: Instruction, data: int) -> None:
        """Store accumulator."""
        self._write_memory(data, instruction.mode, self.A)

    def _STX(self, instruction: Instruction, data: int) -> None:
        """Store X register."""
        self._write_memory(data, instruction.mode, self.X)

    def _STY(self, instruction: Instruction, data: int) -> None:
        """Store Y register."""
        self._write_memory(data, instruction.mode, self.Y)

    def _TAX(self, instruction: Instruction, data: int) -> None:
        """Transfer A to X."""
        self.X = self.A
        self._setZN(self.X)

    def _TAY(self, instruction: Instruction, data: int) -> None:
        """Transfer A to Y."""
        self.Y = self.A
        self._setZN(self.Y)

    def _TSX(self, instruction: Instruction, data: int) -> None:
        """Transfer stack pointer to X."""
        self.X = self.SP
        self._setZN(self.X)

    def _TXA(self, instruction: Instruction, data: int) -> None:
        """Transfer X to A."""
        self.A = self.X
        self._setZN(self.A)

    def _TXS(self, instruction: Instruction, data: int) -> None:
        """Transfer X to SP."""
        self.SP = self.X

    def _TYA(self, instruction: Instruction, data: int) -> None:
        """Transfer Y to A."""
        self.A = self.Y
        self._setZN(self.A)

    def _noimpl(self, instruction: Instruction, data: int) -> None:
        print(f"{instruction.type.name} is not implmemented.")
