"""Zelda 1 overworld -> an emu-harness Canvas, decoded from the ROM's own map data.

A conversion of the game's code, not a re-derivation: each step names the routine it follows in
aldonunez's zelda1-disassembly (PRG0; the tables below sit at the same offsets in Rev 1).

  screen (128: 16 x 8)  LevelBlockAttrsD & $7F -> layout id           (LayoutRoomOW)
  layout (16 bytes)     one column descriptor per 16-px column:
                        hi nibble = column heap, lo nibble = nth column in that heap
  column heap           square descriptors; bit 7 starts a column, bit 6 repeats the square
                        once, low 6 bits = square index                (LayoutRoomOrCaveOW)
  square index          >= $10: tiles p, p+1, p+2, p+3 from PrimarySquaresOW (column-major 2x2)
                        <  $10: four tiles from SecondarySquaresOW     (WriteSquareOW)
  primary $E5-$EA       tile objects drawn as another primary          (CheckTileObject)
  attributes            outer palette (LevelBlockAttrsA & 3) everywhere, inner (LevelBlockAttrsB & 3)
                        over the middle, half a quad on the bottom row (FillPlayAreaAttrs)

Secrets render unfound (they depend on the save's world flags). Play area only: 32 x 22 tiles per
screen, no status bar. Runs on py -3.14 (emu-harness).

  py -3.14 tools/overworld.py [rom] [out.png] [--scale N] [--grid]   (default assets/overworld.png)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from emu_harness.machines.nes import ppu
from emu_harness.machines.nes.canvas import Canvas

from paths import ASSETS, ROM

# PRG offsets (no iNES header), from the disassembly's bins.xml and labels; verified in both revs.
ROOM_LAYOUTS_OW = 0x15418           # Z_05 RoomLayoutsOW: $10 bytes per layout
COLUMN_DIRECTORY_OW = 0x19D0F       # Z_06 ColumnDirectoryOW: 16 CPU addresses in bank 5
PRIMARY_SQUARES_OW = 0x1697C        # Z_05 PrimarySquaresOW: 56 bytes
SECONDARY_SQUARES_OW = PRIMARY_SQUARES_OW + 56   # Z_05 SecondarySquaresOW: 16 x 4 bytes
LEVEL_BLOCK_OW = 0x18400            # LevelBlockAttrsA..F, $80 bytes each (copied to $687E)
LEVEL_INFO_OW = 0x19300             # LevelInfo: palette transfer buf "3F 00 20" + 32 bytes first
COMMON_BG = 0x877F                  # CommonBackgroundPatterns -> PPU $1000 ($700 bytes)
COMMON_MISC = 0x8E7F                # CommonMiscPatterns       -> PPU $1F20 ($E0 bytes)
PATTERN_BLOCK_OW_BG = 0xC93B        # PatternBlockOWBG         -> PPU $1700 ($820 bytes)

BANK5 = 0x14000
COLS, ROWS = 16, 8                  # screens
SCREEN_COLS, SCREEN_ROWS = 32, 22   # play area, tiles


def prg(rom: Path = ROM) -> bytes:
    data = Path(rom).read_bytes()
    return data[16:] if data[:4] == b"NES\x1a" else data


def bg_chr(p: bytes) -> bytes:
    """Pattern table $1000 as TransferCommonPatterns + the OW pattern block leave it."""
    pt = bytearray(0x1000)
    pt[0x000:0x700] = p[COMMON_BG:COMMON_BG + 0x700]
    pt[0x700:0xF20] = p[PATTERN_BLOCK_OW_BG:PATTERN_BLOCK_OW_BG + 0x820]
    pt[0xF20:0x1000] = p[COMMON_MISC:COMMON_MISC + 0xE0]
    return bytes(pt)


def bg_palette(p: bytes) -> list[int]:
    buf = p[LEVEL_INFO_OW:LEVEL_INFO_OW + 3 + 32]
    assert buf[:3] == b"\x3f\x00\x20", buf[:3].hex()
    return list(buf[3:19])


def _column(p: bytes, descriptor: int) -> int:
    """PRG offset of the first square descriptor of a column (the bit-7 scan in LayoutRoomOrCaveOW)."""
    d = COLUMN_DIRECTORY_OW + (descriptor >> 4) * 2
    o = BANK5 + (p[d] | p[d + 1] << 8) - 0x8000
    n = descriptor & 0x0F
    while True:
        if p[o] & 0x80:
            if n == 0:
                return o
            n -= 1
        o += 1


def _primary(p: bytes, index: int) -> int:
    v = p[PRIMARY_SQUARES_OW + index]
    if 0xE5 <= v <= 0xEA:            # CheckTileObject: tile objects show as these primaries
        v = [0xC8, 0xD8, 0xC4, 0xBC, 0xC0, 0xC0][v - 0xE5]
    return v


def _square(p: bytes, index: int) -> list[int]:
    """Four tiles in column-major order: (c,r), (c,r+1), (c+1,r), (c+1,r+1). WriteSquareOW."""
    if index >= 0x10:
        t = _primary(p, index)
        return [t, t + 1, t + 2, t + 3]
    return list(p[SECONDARY_SQUARES_OW + index * 4:SECONDARY_SQUARES_OW + index * 4 + 4])


def _attrs(p: bytes, screen: int) -> bytes:
    """PlayAreaAttrs: the 6 attribute-table rows under the play area. FillPlayAreaAttrs."""
    sel = [0x00, 0x55, 0xAA, 0xFF]   # RoomPaletteSelectorToNTAttr
    outer = sel[p[LEVEL_BLOCK_OW + screen] & 3]
    inner = sel[p[LEVEL_BLOCK_OW + 0x80 + screen] & 3]
    a = bytearray([outer] * 0x30)
    for y in range(0x09, 0x27):
        if y & 7 in (0, 7):
            continue
        a[y] = (inner & 0x0F) | (a[y] & 0xF0) if y >= 0x21 else inner
    return bytes(a)


def screen(p: bytes, n: int) -> Canvas:
    """One overworld screen's play area (32 x 22 tiles)."""
    layout = (p[LEVEL_BLOCK_OW + 0x180 + n] & 0x7F) * 16
    cv = Canvas.blank(SCREEN_COLS, SCREEN_ROWS)
    for c in range(16):
        o = _column(p, p[ROOM_LAYOUTS_OW + layout + c])
        repeat = False
        for r in range(11):
            d = p[o]
            t = _square(p, d & 0x3F)
            for i, (dc, dr) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
                cv.tiles[(r * 2 + dr) * SCREEN_COLS + c * 2 + dc] = t[i]
            if d & 0x40 and not repeat:
                repeat = True                # draw it again before moving on
            else:
                repeat = False
                o += 1
    attr = _attrs(p, n)
    cv.subpal = [ppu.attr_subpalette(attr, c, r) for r in range(SCREEN_ROWS) for c in range(SCREEN_COLS)]
    return cv


def world(p: bytes) -> Canvas:
    """All 128 screens, room id = row * 16 + col, as one 512 x 176 tile canvas."""
    cv = Canvas.blank(COLS * SCREEN_COLS, ROWS * SCREEN_ROWS)
    for n in range(COLS * ROWS):
        cv.paste(screen(p, n), (n % COLS) * SCREEN_COLS, (n // COLS) * SCREEN_ROWS)
    return cv


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("rom", nargs="?", default=str(ROM))
    ap.add_argument("out", nargs="?", default=str(ASSETS / "overworld.png"))
    ap.add_argument("--scale", type=int, default=1)
    ap.add_argument("--grid", action="store_true", help="mark screen edges")
    a = ap.parse_args()
    p = prg(Path(a.rom))
    img = world(p).render(bg_chr(p), bg_palette(p), scale=a.scale, master=ppu.NES_MASTER_FCEUX)
    if a.grid:
        from PIL import ImageDraw
        d, w, h = ImageDraw.Draw(img), SCREEN_COLS * 8 * a.scale, SCREEN_ROWS * 8 * a.scale
        for i in range(1, COLS):
            d.line([(i * w, 0), (i * w, img.height)], fill=(255, 0, 255))
        for i in range(1, ROWS):
            d.line([(0, i * h), (img.width, i * h)], fill=(255, 0, 255))
    img.save(a.out)
    print(f"wrote {a.out} ({img.width}x{img.height}, 128 screens)")


if __name__ == "__main__":
    main()
