"""Verify tools/overworld.py against the game itself, two ways (row O4 oracle, 2026-10-26).

1. live:  boot Rev 1 in Mesen (emu-harness), register a name, start file 1, and compare the start
          screen ($77) the PPU shows (nametable rows 8-29 + attributes, pattern table $1000, BG
          palette) with the decoder.
2. code:  from that moment's RAM + WRAM, run the ROM's own LayoutRoomOW ($A9F4) and
          FillPlayAreaAttrs ($83D7), bank 5, on emu-harness's 6502 core for all 128 room ids, and
          compare PlayAreaTiles ($6530) and PlayAreaAttrs ($530) with the decoder.

The battery save is moved aside by emu-harness (Saves/emu-harness-backup/), never deleted.
2026-10-26: live EXACT on $77 (also $67 $76 $78 walked by hand), code EXACT 128/128.

  py -3.14 tools/verify_overworld.py [rom]
"""
from __future__ import annotations

import sys
from pathlib import Path

from emu_harness.cpu.m6502.cpu import CPU6502
from emu_harness.machines.nes import NES, ppu
from emu_harness.machines.nes.canvas import Canvas

import overworld as OW

LAYOUT_ROOM_OW, FILL_PLAY_AREA_ATTRS, DONE = 0xA9F4, 0x83D7, 0xFFF0
PLAY_AREA_TILES, PLAY_AREA_ATTRS, ROOM_ID = 0x6530, 0x530, 0xEB
# Power-on -> overworld: title, Start; REGISTER YOUR NAME; "AAA"; Select x3 to END, Start; file 1.
BOOT = [("wait", 120), ("start", 1), ("wait", 30), ("start", 1), ("wait", 30), ("a", 3),
        ("select", 3), ("start", 1), ("wait", 40), ("start", 1), ("wait", 200)]


def boot(m):
    for b, n in BOOT:
        if b == "wait":
            m.step(frames=n)
        else:
            for _ in range(n):
                m.step([b], frames=4); m.step(frames=20)


class _Mem:
    """CPU space with ROM read-only."""
    def __init__(self, b): self.b = b
    def read(self, a): return self.b[a & 0xFFFF]
    def write(self, a, v):
        if a & 0xFFFF < 0x8000: self.b[a & 0xFFFF] = v & 0xFF
    def read_word(self, a): return self.read(a) | self.read(a + 1) << 8
    def write_word(self, a, v): self.write(a, v); self.write(a + 1, v >> 8)


def _call(space: bytearray, pc: int, a: int = 0) -> bytearray:
    cpu = CPU6502(_Mem(bytearray(space)))
    cpu.sp, cpu.a, cpu.pc = 0xFF, a, pc
    cpu.push_word(DONE - 1)
    cpu.run_until({DONE})
    return cpu.mem.b


def code_oracle(p: bytes, ram: bytes, wram: bytes) -> list[str]:
    space = bytearray(0x10000)
    space[:0x800], space[0x6000:0x8000] = ram, wram
    space[0x8000:0xC000], space[0xC000:] = p[0x14000:0x18000], p[0x1C000:0x20000]
    bad = []
    for n in range(128):
        space[ROOM_ID] = n
        t = _call(space, LAYOUT_ROOM_OW)
        g = _call(t, FILL_PLAY_AREA_ATTRS, a=n)
        attr = bytes(g[PLAY_AREA_ATTRS:PLAY_AREA_ATTRS + 0x30])
        want = Canvas(32, 22, [t[PLAY_AREA_TILES + c * 0x16 + r] for r in range(22) for c in range(32)],
                      [ppu.attr_subpalette(attr, c, r) for r in range(22) for c in range(32)])
        if OW.screen(p, n) != want:
            bad.append(f"{n:02x}")
    return bad


def main():
    rom = Path(sys.argv[1]) if len(sys.argv) > 1 else OW.ROM
    p = OW.prg(rom)
    with NES(rom) as m:
        boot(m)
        room = m.ram(ROOM_ID)[0]
        live = Canvas.from_nametable(m.read("nesNametableRam", 0, 0x400)).crop(0, 8, 32, 22)
        chr_live, pal = m.read("nesChrRam", 0x1000, 0x1000), list(m.read("nesPaletteRam", 0, 16))
        ram, wram = m.ram(0, 0x800), m.ram(0x6000, 0x2000)
    checks = {f"live room {room:02x} tiles+subpal": OW.screen(p, room) == live,
              "live pattern table $1000": OW.bg_chr(p) == chr_live,
              "live BG palette": OW.bg_palette(p) == pal}
    bad = code_oracle(p, ram, wram)
    checks[f"code LayoutRoomOW x128 ({128 - len(bad)}/128)"] = not bad
    for k, v in checks.items():
        print(("EXACT " if v else "DIFF  ") + k)
    if bad:
        print("differing rooms:", " ".join(bad))
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
