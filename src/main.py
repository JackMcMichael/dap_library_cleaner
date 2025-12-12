"""
DAP compatability scan & deletion helper

Scan a Music folder, report potential compatibility issues, and optionally delete
junk files that confuse simple DAP library scanners.

WARNING: Deletions are permanent. You should only run this code on a copy of your data,
for example when preparing an SD card for use exclusively with your DAP.
"""


from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
import re


# Configuration constants

AUDIO_EXTS = {
    ".flac", ".mp3", ".wav", ".aac", ".m4a", ".ogg", ".opus", ".wma", ".ape", ".aiff"
}

# JPG is safest; PNG sometimes works but can be slow/buggy on some DAPs.
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Files that frequently break or clutter DAP indexing
JUNK_EXTS = {
    ".m3u", ".m3u8", ".pls", ".wpl", ".xspf",
    ".db", ".ini", ".log", ".tmp", ".bak",
    ".sfk", ".asd", ".pkf", ".xml", ".json",
}

# Optional sidecars; some devices ignore them, some choke on them
POTENTIALLY_PROBLEMATIC_EXTS = {".cue", ".nfo", ".txt", ".rtf", ".pdf", ".md"}

JUNK_FILENAMES = {"thumbs.db", "desktop.ini", ".ds_store"}
JUNK_DIRNAMES = {".spotlight-v100", ".trashes", "__macosx"}

APPLEDOUBLE_PREFIX = "._"  # macOS AppleDouble sidecars

# Path/filename health checks
DEPTH_LIMIT = 6                 # conservative DAP-friendly limit
REL_PATH_LEN_LIMIT = 180        # conservative DAP-friendly limit
MAX_FILENAME_LEN = 120

# Matches characters that often break filesystems or DAP firmware:
# Windows-invalid symbols and ASCII control characters (0x00–0x1F)
BAD_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1F]')

PREFERRED_COVER_NAMES = {"cover", "folder", "front", "album"}


# Types

@dataclass
class Finding:
    path: Path
    reason: str


# Detectors

def has_non_ascii(s: str) -> bool:
    return any(ord(ch) > 127 for ch in s)

def classify_file(p: Path) -> tuple[str, str]:
    """Return (bucket, reason)"""
    name_lower = p.name.lower()
    ext_lower = p.suffix.lower()

    if p.name.startswith(APPLEDOUBLE_PREFIX):
        return "junk", "macOS AppleDouble sidecar (._*)"

    if name_lower in JUNK_FILENAMES:
        return "junk", f"junk metadata file ({p.name})"

    if ext_lower in AUDIO_EXTS:
        return "allowed", "audio file"

    if ext_lower in IMAGE_EXTS:
        stem = p.stem.lower()
        if stem not in PREFERRED_COVER_NAMES and "cover" not in stem and "folder" not in stem:
            return "maybe", "image file (artwork) but name not cover/folder/front (album art pickup may suffer)"
        return "allowed", "cover art image"

    if ext_lower in JUNK_EXTS:
        return "junk", f"junk sidecar/playlist/db/log ({ext_lower})"

    if ext_lower in POTENTIALLY_PROBLEMATIC_EXTS:
        return "maybe", f"non-audio sidecar ({ext_lower}) — sometimes confuses DAP scans"

    return "unknown", f"unknown file type ({ext_lower or 'no extension'})"


def file_health_checks(p: Path, root: Path) -> list[str]:
    reasons: list[str] = []
    rel = p.relative_to(root)
    rel_str = str(rel)

    depth = len(rel.parts)
    if depth > DEPTH_LIMIT:
        reasons.append(f"deep folder nesting (depth={depth}, limit={DEPTH_LIMIT})")

    if len(rel_str) > REL_PATH_LEN_LIMIT:
        reasons.append(f"long relative path ({len(rel_str)} chars, limit={REL_PATH_LEN_LIMIT})")

    if len(p.name) > MAX_FILENAME_LEN:
        reasons.append(f"very long filename ({len(p.name)} chars, limit={MAX_FILENAME_LEN})")

    if has_non_ascii(rel_str):
        reasons.append("contains non-ASCII characters (possible emojis/unicode)")

    if BAD_CHARS_PATTERN.search(p.name):
        reasons.append("filename contains characters that can break devices (<>:\"/\\|?* or control chars)")

    if p.name != p.name.strip():
        reasons.append("filename has leading/trailing spaces")

    if "  " in p.name:
        reasons.append("filename contains double spaces")

    try:
        if p.stat().st_size == 0:
            reasons.append("zero-byte file")
    except Exception:
        reasons.append("could not stat file (permissions/corruption)")

    return reasons


# UI helpers

def prompt_music_folder() -> Path:
    raw = input('Paste the FULL path to your Music folder:\n> ').strip().strip('"')
    p = Path(raw).expanduser()
    return p.resolve() if p.exists() else p

def print_samples(title: str, items: list[Finding], root: Path, limit: int = 50) -> None:
    print(f"\n{title} (showing up to {limit}):")
    for f in items[:limit]:
        try:
            rel = f.path.relative_to(root)
        except Exception:
            rel = f.path
        print(f"  - {rel}  [{f.reason}]")
    if len(items) > limit:
        print(f"  ...and {len(items) - limit} more")


# main

def main() -> None:
    print("=== Snowsky Echo Mini – Library Cleaner + Compatibility Scanner ===\n")

    root = prompt_music_folder()
    if not root.exists() or not root.is_dir():
        print(f"\n❌ Invalid folder:\n{root}")
        return

    print(f"\nScanning:\n{root}\n")

    buckets: dict[str, list[Finding]] = defaultdict(list)
    issues: list[Finding] = []
    junk_dirs: list[Path] = []

    for d in root.rglob("*"):
        if d.is_dir() and d.name.lower() in JUNK_DIRNAMES:
            junk_dirs.append(d)

    for p in root.rglob("*"):
        if not p.is_file():
            continue

        bucket, reason = classify_file(p)
        buckets[bucket].append(Finding(p, reason))

        for r in file_health_checks(p, root):
            issues.append(Finding(p, r))

    # Summary
    print("=== Summary ===")
    print(f"✅ Allowed (audio/art): {len(buckets['allowed'])}")
    print(f"🧨 Junk (safe to delete): {len(buckets['junk'])}")
    print(f"⚠️  Potentially problematic (optional): {len(buckets['maybe'])}")
    print(f"❓ Unknown file types: {len(buckets['unknown'])}")
    print(f"🧾 Path/filename/zero-byte issues: {len(issues)}")
    if junk_dirs:
        print(f"🗂️  Junk directories detected: {len(junk_dirs)}")

    if buckets["junk"]:
        print_samples("🧨 Junk files", buckets["junk"], root)
    if buckets["maybe"]:
        print_samples("⚠️ Potentially problematic files", buckets["maybe"], root)
    if buckets["unknown"]:
        print_samples("❓ Unknown files", buckets["unknown"], root)
    if issues:
        print_samples("🧾 Name/path issues", issues, root)

    if junk_dirs:
        print("\n🗂️ Junk directories found (often created by macOS):")
        for d in junk_dirs[:30]:
            print("  -", d.relative_to(root))
        if len(junk_dirs) > 30:
            print(f"  ...and {len(junk_dirs) - 30} more")

    # Choose deletion aggressiveness
    print("\n=== Deletion options ===")
    print("1) Delete ONLY 🧨 junk files (recommended)")
    print("2) Delete 🧨 junk + ⚠️ potentially problematic files")
    print("3) Delete 🧨 junk + ⚠️ maybe + ❓ unknown (aggressive)")
    print("4) Report only (no deletions)")
    choice = input("\nChoose 1/2/3/4: ").strip()

    if choice not in {"1", "2", "3", "4"}:
        print("\n❌ Invalid choice. Exiting.")
        return
    if choice == "4":
        print("\n✅ Report complete. No files were deleted.")
        return

    delete_list: list[Path] = []
    delete_list.extend([f.path for f in buckets["junk"]])
    if choice in {"2", "3"}:
        delete_list.extend([f.path for f in buckets["maybe"]])
    if choice == "3":
        delete_list.extend([f.path for f in buckets["unknown"]])

    if not delete_list:
        print("\nNothing selected for deletion.")
        return

    print(f"\nYou are about to permanently delete {len(delete_list)} file(s).")
    confirm = input('Type DELETE to confirm: ').strip()
    if confirm != "DELETE":
        print("\n❎ Cancelled. No files were deleted.")
        return

    deleted = 0
    failed = 0
    for p in delete_list:
        try:
            p.unlink()
            deleted += 1
        except Exception as e:
            failed += 1
            print(f"FAILED: {p} -> {e}")

    print(f"\n🧹 Done. Deleted {deleted} file(s). Failed: {failed}")

    # Optionally remove empty folders (including junk dirs)
    remove_empty = input("\nRemove empty folders too? (y/n): ").strip().lower()
    if remove_empty == "y":
        removed_dirs = 0
        for d in sorted([x for x in root.rglob("*") if x.is_dir()], reverse=True):
            try:
                next(d.iterdir())
            except StopIteration:
                try:
                    d.rmdir()
                    removed_dirs += 1
                except Exception:
                    pass
        print(f"📁 Removed {removed_dirs} empty folder(s).")


if __name__ == "__main__":
    main()