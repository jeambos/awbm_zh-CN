#!/usr/bin/env python3
"""Extract part title pages from Chinese chapter files and create {n}.0.title.md files.

For each part (1-7), reads the first chapter file, extracts the :::tip block
(part title + optional translator's note), creates a title page, and removes
the block from the chapter file.
"""
import re
from pathlib import Path

CHINESE_DIR = Path(__file__).parent / "chinese"

# Mapping: part_dir -> (part_number_prefix, first_chapter_filename)
PARTS = {
    "part0.preface": ("0", "0.1.intro.md"),
    "part1":         ("1", "1.01.md"),
    "part2":         ("2", "2.14.md"),
    "part3":         ("3", "3.26.md"),
    "part4":         ("4", "4.41.md"),
    "part5":         ("5", "5.49.md"),
    "part6":         ("6", "6.59.md"),
    "part7":         ("7", "7.66.md"),
    "part9.appendix": ("8", "8.1.settings.md"),
}


def read_body(filepath):
    """Read file content after YAML front matter (between --- markers)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split on --- boundaries
    parts = content.split('---')
    if len(parts) >= 3:
        # Standard YAML front matter: first ---, YAML, second ---, then body
        yaml_block = parts[1]
        body = '---'.join(parts[2:])
    else:
        body = content

    return body, yaml_block


def extract_tip_block(body):
    """Extract :::tip[...] block from body. Returns (block_text, rest_of_body) or (None, body)."""
    lines = body.split('\n')
    tip_start = None
    tip_end = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(':::tip'):
            tip_start = i
        if tip_start is not None and stripped == ':::':
            tip_end = i
            break

    if tip_start is not None and tip_end is not None:
        block_lines = lines[tip_start:tip_end + 1]
        rest_lines = lines[:tip_start] + lines[tip_end + 1:]
        return '\n'.join(block_lines), '\n'.join(rest_lines)

    return None, body


def make_title_frontmatter(part_num_prefix, title_text):
    """Create YAML front matter for the title page."""
    # Map part prefix to slug path
    slug_map = {
        "0": "frontmatter",
        "1": "part1",
        "2": "part2",
        "3": "part3",
        "4": "part4",
        "5": "part5",
        "6": "part6",
        "7": "part7",
        "8": "appendix",
    }
    slug_path = slug_map.get(part_num_prefix, f"part{part_num_prefix}")

    # Clean title for display
    display_title = title_text.strip().strip('*').strip()
    # Remove bold markers
    display_title = re.sub(r'\*\*(.*?)\*\*', r'\1', display_title)

    return f"""---
title: "{display_title}"
slug: "books/beyond-monogamy/{slug_path}/title"
description: ""
---"""


def process_part(part_dir, num_prefix, first_chapter):
    """Process one part: extract tip block, create title page, update chapter file."""
    part_path = CHINESE_DIR / part_dir
    chapter_path = part_path / first_chapter

    if not chapter_path.exists():
        print(f"  SKIP {part_dir}: {first_chapter} not found")
        return

    body, yaml_block = read_body(chapter_path)
    tip_block, rest_body = extract_tip_block(body)

    if tip_block is None:
        print(f"  SKIP {part_dir}: no :::tip block found in {first_chapter}")
        return

    # Build the title page content
    # Extract the tip title from :::tip[TITLE]
    title_match = re.search(r':::tip\[(.+?)\]', tip_block, re.DOTALL)
    if title_match:
        tip_title = title_match.group(1)
    else:
        tip_title = tip_block

    # The title page content = YAML + the tip block (renamed to heading)
    # Convert :::tip[TITLE] -> # TITLE as main heading, keep translator note as body
    inner_content = tip_block
    inner_content = re.sub(
        r':::tip\[(.+?)\]',
        lambda m: f'# {m.group(1).strip()}',
        inner_content,
        count=1
    )
    # The rest of the admonition text (translator's note) stays as body
    inner_content = inner_content.replace('\n:::', '')

    # Clean up extra blank lines
    inner_content = re.sub(r'\n{3,}', '\n\n', inner_content).strip()

    frontmatter = make_title_frontmatter(num_prefix, tip_title)

    # Write title page
    title_filename = f"{num_prefix}.0.title.md"
    title_path = part_path / title_filename
    with open(title_path, 'w', encoding='utf-8') as f:
        f.write(frontmatter + '\n\n' + inner_content + '\n')

    print(f"  CREATED {part_dir}/{title_filename}")

    # Remove tip block from original chapter file, clean up extra blank lines
    # Reconstruct original file with front matter + rest_body
    rest_body = re.sub(r'\n{3,}', '\n\n', rest_body).strip()
    with open(chapter_path, 'r', encoding='utf-8') as f:
        original = f.read()
    original_parts = original.split('---')
    if len(original_parts) >= 3:
        new_content = '---' + original_parts[1] + '---' + '\n\n' + rest_body + '\n'
    else:
        new_content = rest_body

    with open(chapter_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"  UPDATED {part_dir}/{first_chapter} (removed part title)")


def main():
    for part_dir, (num_prefix, first_chapter) in sorted(PARTS.items()):
        process_part(part_dir, num_prefix, first_chapter)

    print("\nDone.")


if __name__ == "__main__":
    main()
