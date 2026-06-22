#!/usr/bin/env python3
"""Fix bold markers in existing title pages and create missing ones for part0 and part9."""
import re
from pathlib import Path

CHINESE_DIR = Path(__file__).parent / "chinese"

# Parts to fix: their category labels for reference
CATEGORY_LABELS = {
    "part0.preface": "前置内容",
    "part1": "第一部分 外面的世界很精彩",
    "part2": "第二部分 CNM不是一种行为，而是行事的方式",
    "part3": "第三部分 诱象陷阱",
    "part4": "第四部分 这不合逻辑，舰长！",
    "part5": "第五部分 ~~爱会杀人~~ 爱的技能",
    "part6": "第六部分 这就是政治，不是吗？",
    "part7": "第七部分：他人即地狱",
    "part9.appendix": "附录",
}

SLUG_MAP = {
    "part0.preface": "frontmatter",
    "part1": "part1",
    "part2": "part2",
    "part3": "part3",
    "part4": "part4",
    "part5": "part5",
    "part6": "part6",
    "part7": "part7",
    "part9.appendix": "appendix",
}


def fix_title_page(filepath):
    """Fix bold markers **text** -> text in a title page heading."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix heading: remove ** markers
    content = re.sub(r'^# \*\*(.+?)\*\*\s*$', r'# \1', content, flags=re.MULTILINE)
    content = re.sub(r'^# \*\*(.+?)\*\*$', r'# \1', content, flags=re.MULTILINE)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def create_missing_title(part_dir, label):
    """Create a simple title page for parts without :::tip blocks."""
    part_path = CHINESE_DIR / part_dir

    # Determine part number prefix from directory name
    m = re.match(r'part(\d+)', part_dir)
    if not m:
        return
    part_num = m.group(1)
    slug_path = SLUG_MAP.get(part_dir, f"part{part_num}")

    # For appendix, use the existing file numbering convention
    if part_dir == "part9.appendix":
        title_filename = f"{part_num}.0.title.md"
    else:
        title_filename = f"{part_num}.0.title.md"

    title_path = part_path / title_filename
    if title_path.exists():
        print(f"  EXISTS {part_dir}/{title_filename}")
        return

    frontmatter = f"""---
title: "{label}"
slug: "books/beyond-monogamy/{slug_path}/title"
description: ""
---

# {label}
"""

    with open(title_path, 'w', encoding='utf-8') as f:
        f.write(frontmatter)
    print(f"  CREATED {part_dir}/{title_filename}")


def main():
    # Fix bold markers in existing title pages
    for part_dir in sorted(CATEGORY_LABELS.keys()):
        part_path = CHINESE_DIR / part_dir
        m = re.match(r'part(\d+)', part_dir)
        part_num = m.group(1)

        # Find the title page file
        title_files = list(part_path.glob(f"{part_num}.0.title.md"))
        if not title_files:
            # Try for appendix
            if part_dir == "part9.appendix":
                title_files = list(part_path.glob(f"{part_num}.0.title.md"))

        for tf in title_files:
            fix_title_page(tf)
            print(f"  FIXED {part_dir}/{tf.name}")

    # Create missing title pages for part0 and part9
    create_missing_title("part0.preface", "前置内容")
    create_missing_title("part9.appendix", "附录")

    print("\nDone.")


if __name__ == "__main__":
    main()
