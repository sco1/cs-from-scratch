import itertools
from array import array

import numpy as np

from cs_from_scratch.NESEmulator.rom import ROM

SPR_RAM_SIZE = 256
NAMETABLE_SIZE = 2048
PALETTE_SIZE = 32
NES_WIDTH = 256
NES_HEIGHT = 240
# fmt: off
NES_PALETTE = [
    0x7C7C7C, 0x0000FC, 0x0000BC, 0x4428BC, 0x940084, 0xA80020,
    0xA81000, 0x881400, 0x503000, 0x007800, 0x006800, 0x005800,
    0x004058, 0x000000, 0x000000, 0x000000, 0xBCBCBC, 0x0078F8,
    0x0058F8, 0x6844FC, 0xD800CC, 0xE40058, 0xF83800, 0xE45C10,
    0xAC7C00, 0x00B800, 0x00A800, 0x00A844, 0x008888, 0x000000,
    0x000000, 0x000000, 0xF8F8F8, 0x3CBCFC, 0x6888FC, 0x9878F8,
    0xF878F8, 0xF85898, 0xF87858, 0xFCA044, 0xF8B800, 0xB8F818,
    0x58D854, 0x58F898, 0x00E8D8, 0x787878, 0x000000, 0x000000,
    0xFCFCFC, 0xA4E4FC, 0xB8B8F8, 0xD8B8F8, 0xF8B8F8, 0xF8A4C0,
    0xF0D0B0, 0xFCE0A8, 0xF8D878, 0xD8F878, 0xB8F8B8, 0xB8F8D8,
    0x00FCFC, 0xF8D8F8, 0x000000, 0x000000,
]
# fmt: on


class PPU:
    """
    Emulation of the NES Picture Processing Unit (PPU).

    For the purposes of this emulator, `PPU` emulates the entire screen per-frame rather than
    generating per-pixel or per-scanline.
    """

    scanline: int
    cycle: int
    generate_nmi: bool

    spr: array[int]
    display_buffer: np.ndarray

    def __init__(self, rom: ROM) -> None:
        self.rom = rom

        # PPU Memory
        self.spr = array("B", [0] * SPR_RAM_SIZE)  # Sprite RAM
        self.nametables = array("B", [0] * NAMETABLE_SIZE)  # Nametable RAM
        self.palette = array("B", [0] * PALETTE_SIZE)  # Palette RAM

        # Registers
        self.addr = 0  # Main PPU address register
        self.addr_write_latch = False
        self.status = 0
        self.spr_addr = 0

        # Variables controlled by PPU control registers
        self.nametable_addr = 0
        self.addr_increment = 1
        self.spr_pattern_table_addr = 0
        self.bg_pattern_table_addr = 0
        self.generate_nmi = False
        self.show_background = False
        self.show_sprites = False
        self.left_8_sprite_show = False
        self.left_8_background_show = False

        # Internal helper variables
        self.buffer2007 = 0
        self.scanline = 0
        self.cycle = 0

        # Pixels for screen
        self.display_buffer = np.zeros((NES_WIDTH, NES_HEIGHT), dtype=np.uint32)

    def step(self) -> None:
        """
        Emulate a single PPU cycle.

        For the purposes of this emulator, the screen is rendered per-frame rather than generating
        per-pixel or per-scanline.
        """
        # PPU simplified, draw only once per frame
        if (self.scanline == 240) and (self.cycle == 256):
            if self.show_background:
                self._draw_background()

            if self.show_sprites:
                self._draw_sprites(False)

        if (self.scanline == 241) and (self.cycle == 1):
            self.status |= 0b10000000  # Set vblank

        if (self.scanline == 261) and (self.cycle == 1):
            # Vblank off, clear sprite zero, clear sprite overflow
            self.status |= 0b00011111

        # Cycle bookkeeping
        self.cycle += 1
        if self.cycle > 340:
            self.cycle = 0
            self.scanline += 1

            if self.scanline > 261:
                self.scanline = 0

    def _read_memory(self, addr: int) -> int:
        addr = addr % 0x4000  # Mirror >0x4000
        if addr < 0x2000:  # Pattern tables
            return self.rom.read_cartridge(addr)
        elif addr < 0x3F00:  # Nametables
            addr = (addr - 0x2000) % 0x1000  # 3000-3EFF is a mirror
            if self.rom.vertical_mirroring:
                addr = addr % 0x0800
            else:  # horizontal mirroring
                if (addr >= 0x400) and (addr < 0xC00):
                    addr = addr - 0x400
                elif addr >= 0xC00:
                    addr = addr - 0x800
            return self.nametables[addr]
        elif addr < 0x4000:  # Palette memory
            addr = (addr - 0x3F00) % 0x20
            if (addr > 0x0F) and ((addr % 0x04) == 0):
                addr = addr - 0x10
            return self.palette[addr]
        else:
            raise LookupError(f"Error: Unrecognized PPU read at {addr:X}")

    def _write_memory(self, addr: int, val: int) -> None:
        addr = addr % 0x4000  # Mirror >0x4000
        if addr < 0x2000:  # Pattern tables
            return self.rom.write_cartridge(addr, val)
        elif addr < 0x3F00:  # Nametables
            addr = (addr - 0x2000) % 0x1000  # 3000-3EFF is a mirror
            if self.rom.vertical_mirroring:
                addr = addr % 0x0800
            else:  # Horizontal mirroring
                if (addr >= 0x400) and (addr < 0xC00):
                    addr = addr - 0x400
                elif addr >= 0xC00:
                    addr = addr - 0x800
            self.nametables[addr] = val
        elif addr < 0x4000:  # Palette memory
            addr = (addr - 0x3F00) % 0x20
            if (addr > 0x0F) and ((addr % 0x04) == 0):
                addr = addr - 0x10
            self.palette[addr] = val
        else:
            raise LookupError(f"Error: Unrecognized PPU write at {addr:X}")

    def read_register(self, addr: int) -> int:
        """Read memory-mapped register."""
        if addr == 0x2002:  # Status register
            self.addr_write_latch = False
            curr = self.status
            self.status &= 0b01111111  # Clear vblank on read to 0x2002
            return curr
        elif addr == 0x2004:  # Sprite access
            return self.spr[self.spr_addr]
        elif addr == 0x2007:  # PPU memory, read through a buffer
            if (self.addr % 0x4000) < 0x3F00:
                val = self.buffer2007
                self.buffer2007 = self._read_memory(self.addr)
            else:
                val = self._read_memory(self.addr)
                self.buffer2007 = self._read_memory(self.addr - 0x1000)

            # Increment for every read to 0x2007
            self.addr += self.addr_increment
            return val
        else:
            raise LookupError(f"Error: Unrecognized PPU read {addr:X}")

    def write_register(self, addr: int, val: int) -> None:
        """Write to memory-mapped register."""
        if addr == 0x2000:  # Control1
            self.nametable_addr = 0x2000 + (val & 0b00000011) * 0x400

            if val & 0b00000100:
                self.addr_increment = 32
            else:
                self.addr_increment = 1

            self.spr_pattern_table_addr = ((val & 0b00001000) >> 3) * 0x1000
            self.bg_pattern_table_addr = ((val & 0b00010000) >> 4) * 0x1000
            self.generate_nmi = bool(val & 0b10000000)
        elif addr == 0x2001:  # Control2
            self.show_background = bool(val & 0b00001000)
            self.show_sprites = bool(val & 0b00010000)
            self.left_8_background_show = bool(val & 0b00000010)
            self.left_8_sprite_show = bool(val & 0b00000100)
        elif addr == 0x2003:  # Set SPR address
            self.spr_addr = val
        elif addr == 0x2004:  # Set SPR memory & increment address by 1
            self.spr[self.spr_addr] = val
            self.spr_addr += 1
        elif addr == 0x2005:  # Scroll register, not implemented here
            pass
        elif addr == 0x2006:  # Set address
            # Based on: https://wiki.nesdev.org/w/index.php/PPU_scrolling
            # Address is 16 bits but can only be written 1 byte at a time
            if not self.addr_write_latch:
                # First write
                self.addr = (self.addr & 0x00FF) | ((val & 0xFF) << 8)
            else:
                # Second write
                self.addr = (self.addr & 0xFF00) | (val & 0xFF)
            self.addr_write_latch = not self.addr_write_latch
        elif addr == 0x2007:  # Write to memory at address
            self._write_memory(self.addr, val)
            self.addr += self.addr_increment
        else:
            raise LookupError(f"Error: Unrecognized PPU write {addr:X}")

    def _draw_background(self) -> None:
        # Attribute table is always right after the nametable, whose width is 960 bytes
        # The screen is 32 tiles wide & 30 tiles tall, with each tile representing 8x8 pixels
        attr_table_addr = self.nametable_addr + 960
        for x, y in itertools.product(range(32), range(30)):
            tile_addr = self.nametable_addr + y * 32 + x
            nametable_entry = self._read_memory(tile_addr)

            attr_x = x // 4
            attr_y = y // 4
            attr_addr = attr_table_addr + attr_y * 8 + attr_x
            attr_entry = self._read_memory(attr_addr)

            block = (y & 0x02) | ((x & 0x02) >> 1)
            attr_bits = 0
            if block == 0:
                attr_bits = (attr_entry & 0b00000011) << 2
            elif block == 1:
                attr_bits = attr_entry & 0b00001100
            elif block == 2:
                attr_bits = (attr_entry & 0b00110000) >> 2
            elif block == 3:
                attr_bits = (attr_entry & 0b11000000) >> 4
            else:
                print("Invalid block")

            for fine_y in range(8):
                low_order = self._read_memory(
                    self.bg_pattern_table_addr + nametable_entry * 16 + fine_y
                )
                high_order = self._read_memory(
                    self.bg_pattern_table_addr + nametable_entry * 16 + 8 + fine_y
                )

                for fine_x in range(8):
                    pixel = (
                        ((low_order >> (7 - fine_x)) & 1)
                        | (((high_order >> (7 - fine_x)) & 1) << 1)
                        | attr_bits
                    )

                    x_screen_loc = x * 8 + fine_x
                    y_screen_loc = x * 8 + fine_y
                    is_transparent = (pixel & 3) == 0

                    # If the background is transparent, use the first color in the palette
                    if is_transparent:
                        color = self.palette[0]
                    else:
                        color = self.palette[pixel]

                    self.display_buffer[x_screen_loc, y_screen_loc] = NES_PALETTE[color]

    def _draw_sprites(self, background_transparent: bool) -> None:
        # Traverse sprite memory backwards, as the zeroth sprite has special significance
        for i in range(SPR_RAM_SIZE - 4, -4, -4):
            y_pos = self.spr[i]
            if y_pos == 0xFF:  # 0xFF is a marker for no sprite data
                continue

            background_sprite = bool((self.spr[i + 2] >> 5) & 1)
            x_pos = self.spr[i + 3]

            for x in range(x_pos, x_pos + 8):
                if x >= NES_WIDTH:
                    continue

                for y in range(y_pos, y_pos + 8):
                    if y >= NES_HEIGHT:
                        continue

                    # If a sprite is flipped vertically, read its pixels in reverse vertical order
                    flip_y = bool((self.spr[i + 2] >> 7) & 1)
                    sprite_line = y - y_pos
                    if flip_y:
                        sprite_line = 7 - sprite_line

                    idx = self.spr[i + 1]
                    bit0s_addr = self.spr_pattern_table_addr + (idx * 16) + sprite_line
                    bit1s_addr = self.spr_pattern_table_addr + (idx * 16) + sprite_line + 8
                    bit0s = self._read_memory(bit0s_addr)
                    bit1s = self._read_memory(bit1s_addr)
                    bit3and2 = ((self.spr[i + 2]) & 3) << 2

                    flip_x = bool((self.spr[i + 2] >> 6) & 1)
                    x_loc = x - x_pos  # Position within sprite
                    if not flip_x:
                        x_loc = 7 - x_loc

                    bit1and0 = (((bit1s >> x_loc) & 1) << 1) | (((bit0s >> x_loc) & 1) << 0)
                    if bit1and0 == 0:
                        continue  # Skip transparent pixel

                    # The PPU keeps track of whether the zeroth sprite is colliding with any
                    # non-transparent background pixels, called a "sprite-zero hit"
                    # Check that left 8 pixel clipping is not off
                    if (
                        (i == 0)
                        and (not background_transparent)
                        and (
                            not (
                                x < 8
                                and (not self.left_8_sprite_show or not self.left_8_background_show)
                            )
                            and self.show_background
                            and self.show_sprites
                        )
                    ):
                        self.status |= 0b01000000

                    # Still need to cound background sprites for sprite-zero checks
                    if background_sprite and not background_transparent:
                        continue  # Background sprite shouldn't draw over opaque pixels

                    color = bit3and2 | bit1and0
                    color = self._read_memory(0x3F10 + color)  # Accomodate address mirroring
                    self.display_buffer[x, y] = NES_PALETTE[color]
