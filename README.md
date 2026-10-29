# Zelda1-decompiler

The Legend of Zelda (NES, USA Rev 1), read from its own data and code. Early: the overworld only.

Supply your own ROM, `Legend of Zelda, The (USA) (Rev 1).nes`, in the machine's ROM store (emu-harness
`config.toml`, `roms`; this folder works as a fallback). `tools/paths.py` finds it with
`emu_harness.roms.find_rom` and checks the dump: whole-file SHA-1
`4671517d72d09799403f6c672cd2b395933e926e` (headerless `BE2F5DC8C5BA8EC1A344A71F9FB204750AF24FE7`, the
hash BizHawk records). The layout is emu-harness's standard one (`PHASES.md`, Project layout):
`tools/`, renders in `assets/` and captures in `traces/` (both gitignored), and `re-roadmap.toml`
(`py -3.14 -m emu_harness status Zelda1-decompiler`). Tools run on `py -3.14` with
[emu-harness](https://github.com/chrisaacson69/emu-harness) installed; generic NES work (tile
decode, palettes, the canvas, the 6502, Mesen) is library calls into it, never local copies.

| Tool | What |
|---|---|
| `tools/overworld.py` | All 128 overworld screens -> one 512 x 176 tile canvas -> PNG (default `assets/overworld.png`; `--grid`, `--scale`). A conversion of the game's `LayoutRoomOW` / `WriteSquareOW` / `FillPlayAreaAttrs`. |
| `tools/verify_overworld.py` | The oracle: Mesen's live PPU at the start screen, and the ROM's own layout code run on the harness 6502 for all 128 rooms. 2026-10-26: EXACT, 128/128. |

Map of the format, with routine names from aldonunez's
[zelda1-disassembly](https://github.com/aldonunez/zelda1-disassembly) (PRG0; the overworld tables
sit at the same offsets in Rev 1, the common background patterns differ in content): the
docstring of `tools/overworld.py`.
