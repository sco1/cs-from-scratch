from __future__ import annotations

import typing as t
from array import array
from pathlib import Path
from struct import unpack

ROM_SIGNATURE = 0x4E45531A
HEADER_SIZE = 16
TRAINER_SIZE = 512
PRG_ROM_BASE_UNIT_SIZE = 16384
CHR_ROM_BASE_UNIT_SIZE = 8192
PRG_RAM_SIZE = 8192


class Header(t.NamedTuple):
    """
    iNES file format header components.

    The components are assumed to be the following:
        * `signature` - Constant `0x4E45531A` (ASCII `"NES"` followed by MS-DOS EOF)
        * `prg_rom_size` - Size of PRG ROM in 16KB units
        * `chr_rom_size` - Size of CHR ROM in 8KB units (`0` means the board uses CHR RAM)
        * `flags6` - Mapper, mirroring, battery, trainer
        * `flags7` - Mapper, VS/Playchoice, NES 2.0
        * `flags8` - PRG RAM size (rarely used extension)
        * `flags9` - TV system (rarely used extension)
        * `flags10` - TV system, PRG RAM presence (unofficial, rarely used extension)
        * `unused` - Unused padding, usually zero-padded but can contain misc. fingerprinting

    See: https://www.nesdev.org/wiki/INES#iNES_file_format for more information
    """

    signature: int
    prg_rom_size: int
    chr_rom_size: int
    flags6: int
    flags7: int
    flags8: int
    flags9: int
    flags10: int
    unused: bytes

    @classmethod
    def from_bytes(cls, raw_bytes: bytes) -> Header:
        """
        Build an iNES header from the provided big-endian bytes.

        The raw bytes of the iNES file format header are defined as follows:
            * `0-3` - Signature constant `0x4E45531A` (ASCII `"NES"` followed by MS-DOS EOF)
            * `4` - Size of PRG ROM in 16KB units
            * `5` - Size of CHR ROM in 8KB units (value `0` means the board uses CHR RAM)
            * `6` - Flags `6`: mapper, mirroring, battery, trainer
            * `7` - Flags `7`: mapper, VS/Playchoice, NES 2.0
            * `8` - Flags `8`: PRG RAM size (rarely used extension)
            * `9` - Flags `9`: TV system (rarely used extension)
            * `10` - Flags `10`: TV system, PRG RAM presence (unofficial, rarely used extension)
            * `11-15` - Unused padding, usually zero-padded but can contain misc. fingerprinting
        """
        if len(raw_bytes) != HEADER_SIZE:
            raise ValueError(f"Expected {HEADER_SIZE} bytes, received {len(raw_bytes)}")

        # Unpack the bytes into their components:
        #     * `!` indicates the bytes that follow are big-endian
        #     * `L` unpacks 4 bytes as `unsigned long` -> `int`
        #     * `B` unpacks 1 byte as `unsigned char` -> `int`
        #     * `5s` unpacks 5 bytes as `char[]` -> bytes (unused, left as bytes)
        return cls(*unpack("!LBBBBBBB5s", raw_bytes))


class ROM:
    prg_rom: bytes
    chr_rom: bytes
    prg_ram: array[int]

    read_cartridge: t.Callable[[int], int]
    write_cartridge: t.Callable[[int, int], None]

    def __init__(self, rom_file: Path):
        with rom_file.open("rb") as f:
            print("Parsing ROM header...")
            self.header = Header.from_bytes(f.read(HEADER_SIZE))

            if self.header.signature != ROM_SIGNATURE:
                print("Invalid ROM header signature")
            else:
                print("Valid ROM header signature")

            # Parse mapper from the beginning of Flags 6 (lower nibble) & Flags 7 (upper nibble)
            self.mapper = (self.header.flags7 & 0xF0) | (self.header.flags6 & 0xF0 >> 4)
            print(f"Mapper {self.mapper}")

            if self.mapper != 0:
                raise ValueError("Invalid Mapper: Only Mapper 0 is implemented")

            # Though only one mapper is currently supported, use a generic method wrapping to
            # support potential future expansion
            self.read_cartridge = self.read_mapper0
            self.write_cartridge = self.write_mapper0

            # Check if there's a trainer (4th bit in Flags 6) and read it
            self.trainer_data: bytes | None
            self.has_trainer = bool(self.header.flags6 & 4)
            if self.has_trainer:
                print("Has trainer data")
                self.trainer_data = f.read(TRAINER_SIZE)
            else:
                print("No trainer data")
                self.trainer_data = None

            # Check mirroring (0: horizontal mirror, 1: vertical mirror)
            self.vertical_mirroring = bool(self.header.flags6 & 1)
            print(f"Has vertical mirroring: {self.vertical_mirroring}")

            # Read PRG ROM & CHR ROM sizes
            self.prg_rom = f.read(PRG_ROM_BASE_UNIT_SIZE * self.header.prg_rom_size)
            self.chr_rom = f.read(CHR_ROM_BASE_UNIT_SIZE * self.header.chr_rom_size)

            self.prg_ram = array("B", [0] * PRG_RAM_SIZE)

    def read_mapper0(self, addr: int) -> int:
        if addr < 0x2000:  # CHR ROM
            return self.chr_rom[addr]
        elif 0x6000 <= addr < 0x8000:  # PRG RAM
            return self.prg_ram[addr % PRG_RAM_SIZE]
        elif addr >= 0x8000:  # PRG ROM
            if self.header.prg_rom_size > 1:
                return self.prg_rom[addr - 0x8000]
            else:
                return self.prg_rom[(addr - 0x8000) % PRG_ROM_BASE_UNIT_SIZE]
        else:
            raise LookupError(f"Tried to read at invalid address: {addr:X}")

    def write_mapper0(self, addr: int, val: int) -> None:
        if addr >= 0x6000:
            self.prg_ram[addr % PRG_RAM_SIZE] = val
