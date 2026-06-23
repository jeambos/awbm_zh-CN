#!/usr/bin/env python3
"""Clean manual spaces between Chinese/CJK text and western tokens.

Default mode is a dry run. Use --write to update files, or --check to fail when
any target file would change.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TARGET = BASE_DIR / "chinese"

CJK_LEFT = (
    r"\u3400-\u4DBF"
    r"\u4E00-\u9FFF"
    r"\uF900-\uFAFF"
    r"\u3001-\u303F"
    r"\uFF01-\uFF0F"
    r"\uFF1A-\uFF20"
    r"\uFF3B-\uFF40"
    r"\uFF5B-\uFF65"
)
CJK_RIGHT = CJK_LEFT
WESTERN_LEFT = r"A-Za-z0-9%"
WESTERN_RIGHT = r"A-Za-z0-9%"

SPACE_AFTER_CJK = re.compile(rf"([{CJK_LEFT}]) ([{WESTERN_RIGHT}])")
SPACE_BEFORE_CJK = re.compile(rf"([{WESTERN_LEFT}]) ([{CJK_RIGHT}])")
LINK_DESTINATION = re.compile(r"(?<!!)\]\([^)\n]*\)")
INLINE_CODE = re.compile(r"(`+)(.*?)(\1)")
FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass
class FileChange:
    path: Path
    replacements: int
    before: str
    after: str


def clean_text_segment(text: str) -> tuple[str, int]:
    """Clean a plain text segment and return replacement count."""
    total = 0
    previous = None
    while previous != text:
        previous = text
        text, count = SPACE_AFTER_CJK.subn(r"\1\2", text)
        total += count
        text, count = SPACE_BEFORE_CJK.subn(r"\1\2", text)
        total += count
    return text, total


def protect_spans(text: str, pattern: re.Pattern[str], namespace: str) -> tuple[str, list[str]]:
    """Replace protected spans with placeholders that contain no target chars."""
    protected: list[str] = []

    def store(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"\x00{namespace}:{len(protected) - 1}\x00"

    return pattern.sub(store, text), protected


def restore_spans(text: str, protected: list[str], namespace: str) -> str:
    for index, value in enumerate(protected):
        text = text.replace(f"\x00{namespace}:{index}\x00", value)
    return text


def clean_markdown_line(line: str) -> tuple[str, int]:
    """Clean one non-fenced Markdown line while protecting inline code and URLs."""
    line, link_destinations = protect_spans(line, LINK_DESTINATION, "link")
    line, inline_code = protect_spans(line, INLINE_CODE, "code")
    cleaned, replacements = clean_text_segment(line)
    cleaned = restore_spans(cleaned, inline_code, "code")
    cleaned = restore_spans(cleaned, link_destinations, "link")
    return cleaned, replacements


def clean_markdown(text: str) -> tuple[str, int]:
    """Clean Markdown while leaving fenced code blocks untouched."""
    lines = text.splitlines(keepends=True)
    in_fence = False
    output: list[str] = []
    total = 0

    for line in lines:
        if FENCE.match(line):
            in_fence = not in_fence
            output.append(line)
            continue

        if in_fence:
            output.append(line)
            continue

        cleaned, replacements = clean_markdown_line(line)
        output.append(cleaned)
        total += replacements

    return "".join(output), total


def iter_markdown_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() == ".md" else []
    return sorted(path for path in target.rglob("*.md") if path.is_file())


def collect_changes(target: Path) -> list[FileChange]:
    changes: list[FileChange] = []
    for path in iter_markdown_files(target):
        before = path.read_text(encoding="utf-8")
        after, replacements = clean_markdown(before)
        if after != before:
            changes.append(FileChange(path, replacements, before, after))
    return changes


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def first_changed_lines(change: FileChange, limit: int) -> list[str]:
    before_lines = change.before.splitlines()
    after_lines = change.after.splitlines()
    samples: list[str] = []
    for index, (before, after) in enumerate(zip(before_lines, after_lines), start=1):
        if before != after:
            samples.append(f"{relative(change.path)}:{index}\n- {before}\n+ {after}")
            if len(samples) >= limit:
                break
    return samples


def print_summary(changes: list[FileChange], sample_limit: int) -> None:
    total_files = len(changes)
    total_replacements = sum(change.replacements for change in changes)
    print(f"Files with changes: {total_files}")
    print(f"Candidate replacements: {total_replacements}")

    if not changes:
        return

    print("\nTop files:")
    for change in sorted(changes, key=lambda item: item.replacements, reverse=True)[:10]:
        print(f"  {relative(change.path)}: {change.replacements}")

    if sample_limit > 0:
        print("\nSamples:")
        remaining = sample_limit
        for change in changes:
            samples = first_changed_lines(change, remaining)
            for sample in samples:
                print(sample)
            remaining -= len(samples)
            if remaining <= 0:
                break


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove spaces between CJK text/punctuation and western tokens in Markdown files."
    )
    parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        default=DEFAULT_TARGET,
        help="Markdown file or directory to scan; defaults to draft/2026revised/chinese.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Update files in place.")
    mode.add_argument("--check", action="store_true", help="Exit 1 if any file would change.")
    parser.add_argument("--samples", type=int, default=8, help="Number of changed-line samples to print.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    target = args.target.resolve()

    if not target.exists():
        parser.error(f"target does not exist: {target}")

    changes = collect_changes(target)
    print_summary(changes, args.samples)

    if args.write:
        for change in changes:
            change.path.write_text(change.after, encoding="utf-8", newline="")
        print(f"\nUpdated {len(changes)} file(s).")
        return 0

    if args.check and changes:
        print("\nMixed CJK/western spacing remains. Run with --write to apply these changes.")
        return 1

    if changes:
        print("\nDry run only. Run with --write to apply these changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
