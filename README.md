# DAP Compatability Music Library Cleaner

A small Python utility to scan and clean a music library for simple DAPs (Digital Audio Players) like the **Echo Snowsky Mini**.

Frequently file types, structure, metadata and character sets can cause comparability issues when syncing a music library to a DAP.

This should only be run on a folder containing a copy of your music library, for example on an SD card to be used exclusively as DAP storage.

It helps fix common “library not refreshing” issues by detecting and optionally removing:
- macOS sidecar files (`._*`, `.DS_Store`, `__MACOSX`, etc.)
- playlist and database files (`.m3u/.m3u8/.pls/.db/.ini/...`)
- other non-audio clutter that can confuse DAP indexing
- risky path/filename issues (deep folder nesting, long paths, non-ASCII/emojis, zero-byte files, etc.)

> ⚠️ This tool can permanently delete files. Always keep a backup of your music library.

---

## Features

- ✅ Keeps only **audio files** + **album art**
- 🧨 Detects and removes common junk: playlists, DB/log/ini files, macOS metadata
- ⚠️ Flags potential compatibility issues:
  - deep folder nesting / long paths
  - non-ASCII characters (including emojis)
  - filenames with problematic characters
  - zero-byte files
  - artwork naming that may reduce album art pickup

---

## Requirements

- Python 3.10+ (works with standard library only)

---

## Quick start (VS Code)

1. Clone the repo
2. Open in VS Code
3. Run:

```bash
python src/snowsky_library_cleaner.py
