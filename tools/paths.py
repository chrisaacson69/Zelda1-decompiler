"""paths.py - where this project's files are, resolved from this file, never the working directory.

Every tool takes its default paths from here (emu-harness PHASES.md, Project layout), so a tool runs
the same from any cwd and a layout change is an edit to this file alone.
"""
from pathlib import Path

from emu_harness.roms import find_rom

ROOT = Path(__file__).resolve().parents[1]      # the project root (this file is in tools/)

# The ROM is in the machine's ROM store (emu-harness config.toml `roms`), else this repo, and must be
# this dump: Rev 1, whole-file SHA-1 below; headerless SHA-1 BE2F5DC8C5BA8EC1A344A71F9FB204750AF24FE7,
# the hash BizHawk records in the AIBeatsZelda run-6 .bk2 (it leaves the 16-byte header out).
ROM_NAME = "Legend of Zelda, The (USA) (Rev 1).nes"
ROM_SHA1 = "4671517d72d09799403f6c672cd2b395933e926e"
ROM = find_rom(ROM_NAME, ROM_SHA1, fallback=[ROOT], missing_ok=True)

ASSETS = ROOT / "assets"                        # renders (gitignored: ROM-derived)
TRACES = ROOT / "traces"                        # captures (gitignored)
