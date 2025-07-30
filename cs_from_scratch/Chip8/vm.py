import random
import sys
import timeit
from array import array
from enum import IntEnum
from functools import partial

import numpy as np
import pygame

from cs_from_scratch.Chip8 import BEE_SOUND

SCREEN_WIDTH = 64
SCREEN_HEIGHT = 32
SPRITE_WIDTH = 8

RAM_SIZE = 4096
TIMER_DELAY = 1 / 60
FRAME_TIME_EXPECTED = 1 / 500

ALLOWED_KEYS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f")

# fmt: off
FONT_SET = (
    0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
    0x20, 0x60, 0x20, 0x20, 0x70, # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
    0x90, 0x90, 0xF0, 0x10, 0x10, # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
    0xF0, 0x10, 0x20, 0x40, 0x40, # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90, # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
    0xF0, 0x80, 0x80, 0x80, 0xF0, # C
    0xE0, 0x90, 0x90, 0x90, 0xE0, # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
    0xF0, 0x80, 0xF0, 0x80, 0x80, # F
)
# fmt: on


class Colors(IntEnum):  # noqa: D101
    WHITE = 0xFFFFFFFF
    BLACK = 0


BYTEARRAY_P = partial(array, "B")


def run(program_data: bytes, rom_filename: str) -> None:  # noqa: D103
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED)
    pygame.display.set_caption(f"Chip8 - {rom_filename}")

    bee_sound = pygame.mixer.Sound(BEE_SOUND)
    currently_playing_sound = False

    vm = Chip8VM(program_data)
    timer_accumulator = 0.0  # Used to limit the timer to 60 Hz
    while True:
        frame_start = timeit.default_timer()
        vm.step()

        if vm.needs_redraw:
            pygame.surfarray.blit_array(screen, vm.display_buffer)
            pygame.display.flip()

        # Handle keyboard events
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                key_name = pygame.key.name(event.key)
                if key_name in ALLOWED_KEYS:
                    vm.keys[ALLOWED_KEYS.index(key_name)] = True
            elif event.type == pygame.KEYUP:
                key_name = pygame.key.name(event.key)
                if key_name in ALLOWED_KEYS:
                    vm.keys[ALLOWED_KEYS.index(key_name)] = False
            elif event.type == pygame.QUIT:
                sys.exit()

        # Handle sound
        if vm.play_sound:
            if not currently_playing_sound:
                bee_sound.play(-1)
                currently_playing_sound = True
        else:
            currently_playing_sound = False
            bee_sound.stop()

        # Handle timing
        frame_end = timeit.default_timer()
        frame_time = frame_end - frame_start
        timer_accumulator += frame_time

        # Decrement the timers @ 60 Hz
        if timer_accumulator > TIMER_DELAY:
            vm.decrement_timers()
            timer_accumulator = 0

        # Limit the speed of the entire VM to 500 fps
        if frame_time < FRAME_TIME_EXPECTED:
            diff = FRAME_TIME_EXPECTED - frame_time
            pygame.time.delay(int(diff * 1000))
            timer_accumulator += diff


def concat_nibbles(*args: int) -> int:
    """
    Concatenate an abritrary number of integers.

    It is assumed the input ingers are each 4 bits (aka a "nibble").
    """
    result = 0
    for nibble in args:
        # Shift each integer 4 bits to the left & bitwise OR
        result = (result << 4) | nibble

    return result


def bcd(num: int) -> tuple[int, int, int]:
    """
    Calculate the binary-coded decimal (BCD) value of the given integer.

    NOTE: The given integer must be in the range `[0, 1000)`.
    """
    if (num >= 1000) or (num < 0):
        raise ValueError(f"n must be in the range [0, 1000). Received: {num}")

    hundreds = num // 100
    tens = (num % 100) // 10
    ones = (num % 100) % 10

    return (hundreds, tens, ones)


class Chip8VM:
    """The glorious CHIP-8 VM!"""

    needs_redraw: bool

    def __init__(self, program_data: bytes) -> None:
        """Initialize the CHIP-8 mutable state."""
        # Initialize registers & memory constructs
        # General Purpose Registers - CHIP-8 has 17 of these registers
        self.v = BYTEARRAY_P([0] * 16)

        # Index Register
        self.idx = 0

        # Program Counter
        # Starts at 0x200, addresses below this were used by the VM itself in the original CHIP-8
        # machines
        self.pc: int = 0x200

        # Memory - standard 4k on the original CHIP-8 machines
        self.ram = BYTEARRAY_P([0] * RAM_SIZE)

        # Load the font set into the first 80 bytes
        self.ram[0 : len(FONT_SET)] = BYTEARRAY_P(FONT_SET)

        # Copy the program into RAM, starts at byte 512 by convention
        self.ram[512 : (512 + len(program_data))] = BYTEARRAY_P(program_data)

        # Stack
        # In real hardware this is typically limited to 12 or 16 addresses for jumps, but here we
        # will allow it to be unbounded
        self.stack: list[int] = []

        # Graphics buffer
        # The screen is seen as a cartesian plane whose origin is the top left & y-axis oriented
        # downward
        self.display_buffer = np.zeros((SCREEN_WIDTH, SCREEN_HEIGHT), dtype=np.uint32)
        self.needs_redraw = False

        # Timers - simple registers that count down to 0 @ 60 Hz
        self.delay_timer = 0
        self.sound_timer = 0

        # Keypress status - CHIP-8 has 16 keys
        self.keys = [False] * 16

    @property
    def play_sound(self) -> bool:  # noqa: D102
        return self.sound_timer > 0

    def decrement_timers(self) -> None:  # noqa: D102
        if self.delay_timer > 0:
            self.delay_timer -= 1

        if self.sound_timer > 0:
            self.sound_timer -= 1

    def _clear_registers(self) -> None:
        self.delay_timer = 0
        self.sound_timer = 0
        self.v = BYTEARRAY_P([0] * 16)
        self.idx = 0

    def _clear_screen(self) -> None:
        self.display_buffer.fill(0)
        self.needs_redraw = True

    def _draw_sprite(self, x: int, y: int, height: int) -> None:
        """
        Draw a sprite of the specified `height` on-screen at the given `xy` coordinate lookup.

        The `x` and `y` nibbles represent the indices into the v registers where the xy coordinates
        for the top left of the sprite should be located.
        """
        flipped_black = False  # Did drawing this flip any pixels?
        for row in range(height):
            row_bits = self.ram[self.idx + row]  # Sprite begins at the current instruction register

            for col in range(SPRITE_WIDTH):
                px = x + col
                py = y + row
                if (px >= SCREEN_WIDTH) or (py >= SCREEN_HEIGHT):
                    continue  # ignore off-screen pixels

                new_bit = (row_bits >> (7 - col)) & 1
                old_bit = self.display_buffer[px, py] & 1
                if new_bit & old_bit:  # if both set, flip white -> black
                    flipped_black = True

                # CHIP-8 draws by XORing
                new_pixel = new_bit ^ old_bit
                if new_pixel:
                    self.display_buffer[px, py] = Colors.WHITE
                else:
                    self.display_buffer[px, py] = Colors.BLACK

        # Set flipped flag for collision detection purposes
        self.v[0xF] = int(flipped_black)

    def step(self) -> None:  # noqa: D102
        # Examine the opcode in terms of its nibbles
        # Each opcode is 16 bits, made up of the next 2 bytes in memory
        first2 = self.ram[self.pc]
        last2 = self.ram[self.pc + 1]

        # Break into nibbles
        first = (first2 & 0xF0) >> 4
        second = first2 & 0xF
        third = (last2 & 0xF0) >> 4
        fourth = last2 & 0xF

        self.needs_redraw = False
        jumped = False
        match (first, second, third, fourth):
            # Screen clearing and basic jumps
            case (0x0, 0x0, 0xE, 0x0):
                # (00E0) Clear screen
                self._clear_screen()
            case (0x0, 0x0, 0xE, 0xE):
                # (00EE) Return from subroutine
                self.pc = self.stack.pop()
                jumped = True
            case (0x0, n1, n2, n3):
                # (0nnn) Call the program at nnn, reset timers/registers, clear screen
                self.pc = concat_nibbles(n1, n2, n3)  # go to start
                self._clear_registers()
                self._clear_screen()
                jumped = True
            case (0x1, n1, n2, n3):
                # (1nnn) Jump to address nnn without resetting
                self.pc = concat_nibbles(n1, n2, n3)
                jumped = True
            case (0x2, n1, n2, n3):
                # (2nnn) Call the subroutine at nnn
                self.stack.append(self.pc + 2)
                self.pc = concat_nibbles(n1, n2, n3)
                jumped = True

            # Conditional skips
            case (0x3, x, _, _):
                # (3xnn) Skip the next instruction if v[x] equals nn
                if self.v[x] == last2:
                    self.pc += 4  # Consume the current instruction & jump over next
                    jumped = True
            case (0x4, x, _, _):
                # (4xnn) Skip the next instruction if v[x] does not equal nn
                if self.v[x] != last2:
                    self.pc += 4  # Consume the current instruction & jump over next
                    jumped = True
            case (0x5, x, y, _):
                # (5xy_) Skip the next instruction if v[x] equals v[y]
                if self.v[x] == self.v[y]:
                    self.pc += 4  # Consume the current instruction & jump over next
                    jumped = True

            # General-purpose register adjustments, arithmetic, and bit manipulation
            case (0x6, x, _, _):
                # (6xnn) Set v[x] to nn
                self.v[x] = last2
            case (0x7, x, _, _):
                # (7xnn) Add nn to v[x]
                self.v[x] = (self.v[x] + last2) % 256
            case (0x8, x, y, 0x0):
                # (8xy0) Set v[x] to v[y]
                self.v[x] = self.v[y]
            case (0x8, x, y, 0x1):
                # (8xy1) Set v[x] to (v[x] | v[y]) (bitwise OR)
                self.v[x] |= self.v[y]
            case (0x8, x, y, 0x2):
                # (8xy2) Set v[x] to (v[x] & v[y]) (bitwise AND)
                self.v[x] &= self.v[y]
            case (0x8, x, y, 0x3):
                # (8xy3) Set v[x] to (v[x] ^ v[y]) (bitwise XOR)
                self.v[x] ^= self.v[y]
            case (0x8, x, y, 0x4):
                # (8xy4) Add v[y] to v[x] and set the carry flag
                try:
                    self.v[x] += self.v[y]
                    self.v[0xF] = 0  # Indicate no carry flag
                except OverflowError:
                    self.v[x] = (self.v[x] + self.v[y]) % 256
                    self.v[0xF] = 1  # Set carry flag
            case (0x8, x, y, 0x5):
                # (8xy5) Subtract v[y] from v[x] and set the borrow flag
                # Borrow flag is weird and 1 indicates no borrow
                try:
                    self.v[x] -= self.v[y]
                    self.v[0xF] = 1  # Indicate no borrow
                except OverflowError:
                    self.v[x] = (self.v[x] - self.v[y]) % 256
                    self.v[0xF] = 0  # Indicate there was a borrow
            case (0x8, x, _, 0x6):
                # (8xy6) Shift v[x] right one bit and set the flag to the least significant bit
                self.v[0xF] = self.v[x] & 0x1
                self.v[x] >>= 1
            case (0x8, x, y, 0x7):
                # (8xy7) Subtract v[x] from v[y] and store the result in v[x]; set the borrow flag
                try:
                    self.v[x] = self.v[y] - self.v[x]
                    self.v[0xF] = 1  # Indicate no borrow
                except OverflowError:
                    self.v[x] = (self.v[y] - self.v[x]) % 256
                    self.v[0xF] = 0  # Indicate there was a borrow
            case (0x8, x, _, 0xE):
                # (8x_E) Shift v[x] left one bit and set the flag to the most significant bit
                self.v[0xF] = (self.v[x] & 0b10000000) >> 7
                self.v[x] = (self.v[x] << 1) & 0xFF

            # Miscellaneous instructions
            case (0x9, x, y, 0x0):
                # (9xy0) Skip the next instruction if v[x] doesn't equal v[y]
                if self.v[x] != self.v[y]:
                    self.pc += 4  # Consume the current instruction & jump over next
                    jumped = True
            case (0xA, n1, n2, n3):
                # (Annn) Set i to nnn
                self.idx = concat_nibbles(n1, n2, n3)
            case (0xB, n1, n2, n3):
                # (Bnnn) Jump to nnn + v[0]
                self.pc = concat_nibbles(n1, n2, n3) + self.v[0]
                jumped = True
            case (0xC, x, _, _):
                # (Cxnn) Set v[x] to a (<random integer (0-255)> & nn) (bitwise AND)
                self.v[x] = last2 & random.randint(0, 255)
            case (0xD, x, y, n):
                # (Dxyn) Draw a sprite that's n high at (v[x], v[y]); set the flag on a collision
                self._draw_sprite(self.v[x], self.v[y], n)
                self.needs_redraw = True

            # Key and timer instructions
            case (0xE, x, 0x9, 0xE):
                # (Ex9E) Skip to the next instruction if key v[x] is set (pressed)
                if self.keys[self.v[x]]:
                    self.pc += 4  # Consume the current instruction & jump over next
                    jumped = True
            case (0xE, x, 0xA, 0x1):
                # (ExA1) Skip to the next instruction if key v[x] is not set (not pressed)
                if not self.keys[self.v[x]]:
                    self.pc += 4  # Consume the current instruction & jump over next
                    jumped = True
            case (0xF, x, 0x0, 0x7):
                # (Fx07) Set v[x] to the delay timer
                self.v[x] = self.delay_timer
            case (0xF, x, 0x0, 0xA):
                # (Fx0A) Wait until the next key press, then store the key in v[x]
                while True:
                    event = pygame.event.wait()
                    if event.type == pygame.QUIT:
                        sys.exit()
                    if event.type == pygame.KEYDOWN:
                        key_name = pygame.key.name(event.key)
                    if key_name in ALLOWED_KEYS:
                        self.v[x] = ALLOWED_KEYS.index(key_name)
                        break
            case (0xF, x, 0x1, 0x5):
                # (Fx15) Set the delay timer to v[x]
                self.delay_timer = self.v[x]
            case (0xF, x, 0x1, 0x8):
                # (Fx18) Set the sound timer to v[x]
                self.sound_timer = self.v[x]

            # Index register (i) instructions
            case (0xF, x, 0x1, 0xE):
                # (Fx1E) Add v[x] to i
                self.idx += self.v[x]
            case (0xF, x, 0x2, 0x9):
                # (Fx29) Set i to the location of chacter v[x] in the font set
                self.idx = self.v[x] * 5  # Built-in font set is 5 bytes apart
            case (0xF, x, 0x3, 0x3):
                # (Fx33) Store the binary-coded decimal value in v[x] at memory locations i, i+1,
                # and i+2
                hundreds, tens, ones = bcd(self.v[x])
                self.ram[self.idx] = hundreds
                self.ram[self.idx + 1] = tens
                self.ram[self.idx + 2] = ones
            case (0xF, x, 0x5, 0x5):
                # (Fx55) Dump registers v[0] through v[x] in memory, starting at i
                for r in range(x + 1):
                    self.ram[self.idx + r] = self.v[r]
            case (0xF, x, 0x6, 0x5):
                # (Fx65) Store memory from i through i + x in registers v[0] through v[x]
                for r in range(x + 1):
                    self.v[r] = self.ram[self.idx + r]
            case _:
                raise ValueError(
                    f"Unknown opcode: {hex(first), hex(second), hex(third), hex(fourth)}"
                )

        if not jumped:
            # Increment program counter
            # Each CHIP-8 instruction is 2 bytes long
            self.pc += 2
