#!/usr/bin/env python3
"""
Generate a Table of Contents (TOC) of Markdown files and insert it into README.md.

Behavior:
- Scans the repository for `.md` files (recursively) starting at repo root.
- Excludes `.git` and the README.md itself from the TOC entries.
- For each markdown file, extracts the first heading to use as the link text; falls back to a prettified filename.
- Inserts or replaces TOC between markers `<!-- TOC START -->` and `<!-- TOC END -->` in `README.md`.
- If no markers are present, inserts the TOC right after the first top-level heading (`# ...`).

Usage:
    python3 scripts/generate_toc.py
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
TOC_START = "<!-- TOC START -->"
TOC_END = "<!-- TOC END -->"

EXCLUDE_DIRS = {".git", "node_modules", "venv", "env"}


def is_excluded(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def extract_title(md_path: Path) -> str:
    # Try to read the first Markdown heading from the file
    try:
        with md_path.open("r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                # headings like '# Title' or '## Title'
                m = re.match(r"^#{1,6}\s+(.*)", s)
                if m:
                    return m.group(1).strip()
                # fallback: first non-empty line
                if s:
                    return s[:120]
    except Exception:
        pass
    # fallback to filename prettified
    name = md_path.stem
    return name.replace("_", " ").replace("-", " ").strip().title()


def collect_md_files(root: Path):
    files = []
    for p in sorted(root.rglob("*.md")):
        # skip README.md itself (we'll insert into it), and skip files in excluded dirs
        if p.resolve() == README.resolve():
            continue
        if is_excluded(p.relative_to(root)):
            continue
        files.append(p)
    return files


def build_toc(md_files, root: Path) -> str:
    # Group files by top-level (volume) and second-level (book) directories
    from collections import defaultdict

    def prettify_name(name: str) -> str:
        s = re.sub(r"^[0-9]+[_-]*", "", name)
        s = s.replace("_", " ").replace("-", " ").strip()
        return s.title() if s else name

    # volumes -> books -> list of (title, link)
    volumes = defaultdict(lambda: defaultdict(list))
    root_files = []

    for p in md_files:
        rel = p.relative_to(root)
        parts = rel.parts
        title = extract_title(p)
        link = rel.as_posix()
        if len(parts) == 1:
            root_files.append((title, link))
        elif len(parts) >= 2:
            vol = parts[0]
            book = parts[1]
            volumes[vol][book].append((title, link))

    lines = []

    # Files at repo root first
    if root_files:
        lines.append("## Root")
        for title, link in root_files:
            lines.append(f"- [{title}]({link})")
        lines.append("")

    for vol in sorted(volumes.keys()):
        lines.append(f"## {prettify_name(vol)}")
        books = volumes[vol]
        # Files directly under the volume directory (if any) would appear as book keys equal to filename; handled by listing books below.
        for book in sorted(books.keys()):
            lines.append(f"### {prettify_name(book)}")
            for title, link in books[book]:
                lines.append(f"- [{title}]({link})")
            lines.append("")

    return "\n".join(lines).rstrip()


def insert_toc_into_readme(toc_text: str, readme_path: Path):
    original = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

    toc_block = f"{TOC_START}\n\n{toc_text}\n\n{TOC_END}"

    if TOC_START in original and TOC_END in original:
        # replace existing block
        new = re.sub(rf"{re.escape(TOC_START)}.*?{re.escape(TOC_END)}", toc_block, original, flags=re.S)
    else:
        # Insert after first top-level heading (`# `)
        m = re.search(r"^# .*$", original, flags=re.M)
        if m:
            insert_pos = m.end()
            # insert after the heading line and ensure a blank line
            before = original[:insert_pos].rstrip() + "\n\n"
            after = original[insert_pos:].lstrip()
            new = before + toc_block + "\n\n" + after
        else:
            # Prepend at top if no heading found
            new = toc_block + "\n\n" + original
    # backup
    try:
        backup = readme_path.with_suffix(readme_path.suffix + ".bak")
        backup.write_text(original, encoding="utf-8")
    except Exception:
        pass
    readme_path.write_text(new, encoding="utf-8")


def main():
    md_files = collect_md_files(ROOT)
    if not md_files:
        print("No markdown files found to include in TOC.")
        return
    toc_text = build_toc(md_files, ROOT)
    insert_toc_into_readme(toc_text, README)
    print(f"Inserted/updated TOC in {README}")


if __name__ == "__main__":
    main()
