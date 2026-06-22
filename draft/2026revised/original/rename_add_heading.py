#!/usr/bin/env python3
"""Rename files to add heading prefix, sorted by actual numeric order."""
import re
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent


def parse_sort_key(stem):
    """Extract a tuple (primary, secondary) for numeric sorting."""
    if stem == 'Frontispiece':
        return (0, 0)
    # Remove common prefix
    s = stem.replace('World_Beyond_Monogamy_Final_eBook', '')
    if not s:
        return (0, 1)
    s = s.lstrip('-')
    if not s:
        return (0, 2)
    if '.' in s:
        a, b = s.split('.', 1)
        return (int(a), int(b))
    return (int(s), 0)


def sanitize(text, max_len=60):
    """Convert text to a safe filename fragment."""
    text = text.strip().rstrip('.:;!? ')
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    text = text.strip('_')
    return text[:max_len].rstrip('_')


def find_first_title(content):
    """Find first heading or fallback text line."""
    for line in content.split('\n'):
        stripped = line.strip()
        m = re.match(r'^#{1,2}\s+(.+)$', stripped)
        if m:
            return m.group(1).strip()
        if (stripped and not stripped.startswith('![')
                and stripped != '---' and not stripped.startswith('[^')
                and not stripped.startswith('|')):
            return stripped
    return ''


def main():
    md_files = list(OUTPUT_DIR.glob("*.md"))

    # Sort by numeric key
    def sort_fn(p):
        return parse_sort_key(p.stem)

    md_files.sort(key=sort_fn)

    rename_map = {}
    for idx, old_path in enumerate(md_files):
        with open(old_path, 'r', encoding='utf-8') as f:
            content = f.read()

        title = find_first_title(content)
        if not title:
            # Try to infer context from the filename
            stem = old_path.stem
            if 'eBook-29' in stem or 'eBook-30' in stem:
                title = 'Chapter_Twenty'
            elif 'eBook-41' in stem or 'eBook-42' in stem:
                title = 'Chapter_Thirty'
            elif 'eBook-44' in stem or 'eBook-45' in stem:
                title = 'Chapter_Thirty_Two'
            elif 'eBook-13' in stem or 'eBook-14' in stem:
                title = 'Chapter_Six'
            elif 'eBook' in stem and 'eBook-' not in stem:
                title = 'Half_Title_Page'
            elif 'Frontispiece' in stem:
                title = 'Frontispiece_Dedication'
            else:
                title = f'Part_Opener_{idx:03d}'

        slug = sanitize(title)
        if not slug:
            slug = f'page_{idx:03d}'

        new_name = f"{idx:03d}_{slug}.md"
        new_path = OUTPUT_DIR / new_name

        if new_path.exists() and new_path != old_path:
            new_name = f"{idx:03d}_{slug}_{idx}.md"
            new_path = OUTPUT_DIR / new_name

        rename_map[new_name] = (old_path, new_path)

    for new_name, (old_path, new_path) in sorted(rename_map.items()):
        print(f"  {old_path.name:<70s} -> {new_name}")
        old_path.rename(new_path)

    print(f"\nDone. Renamed {len(rename_map)} files.")


if __name__ == "__main__":
    main()
