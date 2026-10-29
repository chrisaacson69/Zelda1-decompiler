# Zelda1-decompiler: app-local rules

A **package in the vault's project process-table**. It obeys, outermost first:

1. **Kernel**: user-global `~/.claude/CLAUDE.md` (grounding: never fabricate, reuse/convert > rebuild,
   missing grounding means find it or ask).
2. **Project SDK**: the vault's `projects/CLAUDE.md`.
3. **emu-harness** `CLAUDE.md` and `PHASES.md`: this repo is a game adapter on that library.
4. **This file.**

## Habits

- **Library code lives in emu-harness**, installed with `pip install -e ../emu-harness`. Never
  `sys.path` into it, and never copy a pass here that the library already has.
- **Paths come from `tools/paths.py`**, resolved from its own file: the ROM (by name and SHA-1, through
  the machine's ROM store) and every output folder. A tool never builds a path from the cwd.
- **aldonunez's zelda1-disassembly is a sibling oracle**: grade against it after deriving, never
  derive from it. It describes PRG0 (Rev 0); this project's ROM is Rev 1.
- **State lives in `re-roadmap.toml`** (`py -3.14 -m emu_harness status Zelda1-decompiler`).
- **No ROMs, saves, renders or captures in git** (`.gitignore`).
- Python is `py -3.14`.
