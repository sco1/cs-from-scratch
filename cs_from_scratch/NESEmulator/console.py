import sys
import timeit

import pygame

from cs_from_scratch.NESEmulator.cpu import CPU
from cs_from_scratch.NESEmulator.ppu import NES_HEIGHT, NES_WIDTH, PPU
from cs_from_scratch.NESEmulator.rom import ROM


def run(rom: ROM, name: str) -> None:
    """Pygame entry point for the NES Emulator."""
    pygame.init()
    screen = pygame.display.set_mode((NES_WIDTH, NES_HEIGHT), 0, 24)
    pygame.display.set_caption(f"NES EMulator - {name}")

    ppu = PPU(rom)
    cpu = CPU(ppu, rom)

    ticks = 0
    start = None
    while True:
        cpu.step()
        new_ticks = cpu.cpu_ticks - ticks
        for _ in range(new_ticks * 3):  # 3 PPU cycles for every CPU tick
            ppu.step()

            # Once per frame, draw everything onto the screen
            if (ppu.scanline == 240) and (ppu.cycle == 257):
                pygame.surfarray.blit_array(screen, ppu.display_buffer)
                pygame.display.flip()

                end = timeit.default_timer()
                if start is not None:
                    print(end - start)
                start = timeit.default_timer()

            if (ppu.scanline == 241) and (ppu.cycle == 2) and ppu.generate_nmi:
                cpu.trigger_NMI()

        ticks += new_ticks

        # Handle keyboard events as joypad changes
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            if event.type not in {pygame.KEYDOWN, pygame.KEYUP}:
                continue

            is_keydown = event.type == pygame.KEYDOWN
            match event.key:
                case pygame.K_LEFT:
                    cpu.joypad1.left = is_keydown
                case pygame.K_RIGHT:
                    cpu.joypad1.right = is_keydown
                case pygame.K_UP:
                    cpu.joypad1.up = is_keydown
                case pygame.K_DOWN:
                    cpu.joypad1.down = is_keydown
                case pygame.K_x:
                    cpu.joypad1.a = is_keydown
                case pygame.K_z:
                    cpu.joypad1.b = is_keydown
                case pygame.K_s:
                    cpu.joypad1.start = is_keydown
                case pygame.K_a:
                    cpu.joypad1.select = is_keydown
                case _:
                    continue
