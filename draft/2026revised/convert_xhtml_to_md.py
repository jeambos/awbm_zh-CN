#!/usr/bin/env python3
"""Convert XHTML files from EPUB to Markdown."""

import os
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

# --- Configuration ---
INPUT_DIR = Path("original_epub")
OUTPUT_DIR = Path("original")
CSS_FILE = Path("css/idGeneratedStyles.css")

# Classes that represent italic text
ITALIC_CLASSES = {
    "CharOverride-10",
    "CharOverride-13",
    "CharOverride-28",
    "CharOverride-29",
    "CharOverride-33",
    "CharOverride-43",
}

# Classes that represent bold text
BOLD_CLASSES = {
    "CharOverride-15",
    "CharOverride-20",
}

# Classes that represent bold italic text
BOLD_ITALIC_CLASSES = {
    "CharOverride-24",
}

# Classes that represent strikethrough text
STRIKETHROUGH_CLASSES = {
    "CharOverride-9",
}

# Classes to discard (no markdown equivalent)
DISCARD_INLINE_CLASSES = {
    "Smallcaps",
    "CharOverride-1",
    "CharOverride-2",
    "CharOverride-3",
    "CharOverride-4",
    "CharOverride-5",
    "CharOverride-6",
    "CharOverride-7",
    "CharOverride-8",
    "CharOverride-11",
    "CharOverride-12",
    "CharOverride-14",
    "CharOverride-18",
    "CharOverride-19",
    "CharOverride-21",
    "CharOverride-22",
    "CharOverride-23",
    "CharOverride-25",
    "CharOverride-26",
    "CharOverride-27",
    "CharOverride-30",
    "CharOverride-31",
    "CharOverride-32",
    "CharOverride-34",
    "CharOverride-35",
    "CharOverride-36",
    "CharOverride-37",
    "CharOverride-38",
    "CharOverride-39",
    "CharOverride-40",
    "CharOverride-41",
    "CharOverride-42",
    "CharOverride-44",
    "_idGenCharOverride-1",
}

# Paragraph classes that indicate body text (normal paragraphs)
BODY_CLASSES = {
    "Body-text",
    "Body-text-no-indent",
    "No-Indent-No-Caps",
    "Body-text-no-indent-Indesign-fix",
    "Copyright",
    "Copyright-First",
    "Dedication",
    "Dedication-no-page-break",
    "Resources",
    "TOC-title-",
    "TOC-text",
    "Basic-Paragraph",
    "Article-Rights-No-Bullets",
    "Bill-of-Rights-No-Bullets",
    "TOC-Header-Page-Break",
}


def get_classes(tag):
    """Get set of classes from a tag."""
    classes = tag.get("class", [])
    if isinstance(classes, str):
        classes = classes.split()
    return set(classes)


def merge_adjacent_formatting(text):
    """Merge adjacent identical markdown formatting separated only by whitespace.
    E.g., *a* *b* -> *a b*, **a** **b** -> **a b**, ***a*** ***b*** -> ***a b***.
    """
    prev = None
    while prev != text:
        prev = text
        # Bold-italic
        text = re.sub(
            r'(?<!\*)\*\*\*([^*]+)\*\*\* +(?<!\*)\*\*\*([^*]+)\*\*\*(?!\*)',
            r'***\1 \2***', text
        )
    prev = None
    while prev != text:
        prev = text
        # Bold
        text = re.sub(
            r'(?<!\*)\*\*([^*]+)\*\* +(?<!\*)\*\*([^*]+)\*\*(?!\*)',
            r'**\1 \2**', text
        )
    prev = None
    while prev != text:
        prev = text
        # Italic
        text = re.sub(
            r'(?<!\*)\*([^*]+)\* +(?<!\*)\*([^*]+)\*(?!\*)',
            r'*\1 \2*', text
        )
    return text


def process_inline(element, footnotes=None):
    """Convert inline elements to markdown text recursively."""
    if footnotes is None:
        footnotes = {}

    result = []
    for content in element.children:
        if isinstance(content, NavigableString):
            text = str(content)
            result.append(text)

        elif isinstance(content, Tag):
            tag_name = content.name

            if tag_name == "br":
                result.append("\n")

            elif tag_name == "img":
                alt = content.get("alt", "")
                src = content.get("src", "")
                result.append(f"![{alt}]({src})")

            elif tag_name == "a":
                href = content.get("href", "")
                epub_type = content.get("epub:type", "")
                inner = process_inline(content, footnotes)

                if epub_type == "noteref":
                    # Footnote reference
                    fn_id = href.split("#")[-1] if "#" in href else ""
                    if fn_id:
                        result.append(f"[^{fn_id}]")
                elif href:
                    # Regular hyperlink
                    result.append(f"[{inner}]({href})")
                elif content.get("id"):
                    # Named anchor (skip)
                    result.append(inner)
                else:
                    result.append(inner)

            elif tag_name == "span":
                classes = get_classes(content)
                inner = process_inline(content, footnotes)

                # Check for markdown formatting
                is_italic = bool(classes & ITALIC_CLASSES)
                is_bold = bool(classes & BOLD_CLASSES)
                is_bold_italic = bool(classes & BOLD_ITALIC_CLASSES)
                is_strikethrough = bool(classes & STRIKETHROUGH_CLASSES)

                # Strip trailing/leading whitespace from formatted spans
                # to avoid issues like *Talk. * rendering
                leading_space = ""
                trailing_space = ""
                stripped = inner
                if inner != inner.lstrip():
                    leading_space = inner[:len(inner) - len(inner.lstrip())]
                    stripped = inner.lstrip()
                if stripped != stripped.rstrip():
                    trailing_space = stripped[len(stripped.rstrip()):]
                    stripped = stripped.rstrip()

                if is_bold_italic or (is_bold and is_italic):
                    result.append(f"{leading_space}***{stripped}***{trailing_space}")
                elif is_bold:
                    if stripped:
                        result.append(f"{leading_space}**{stripped}**{trailing_space}")
                    else:
                        result.append(inner)
                elif is_italic:
                    if stripped:
                        result.append(f"{leading_space}*{stripped}*{trailing_space}")
                    else:
                        result.append(inner)
                elif is_strikethrough:
                    result.append(f"{leading_space}~~{stripped}~~{trailing_space}")
                elif classes & DISCARD_INLINE_CLASSES:
                    # Discard styling, keep text
                    result.append(inner)
                else:
                    # Unknown span classes - keep text
                    result.append(inner)

            elif tag_name == "div":
                # Process div content (might contain nested elements)
                result.append(process_inline(content, footnotes))

            else:
                # Unknown tag - try to get its text
                result.append(process_inline(content, footnotes))

    return merge_adjacent_formatting("".join(result))


def get_text_plain(element):
    """Get plain text content of an element without processing inline formatting."""
    return element.get_text(strip=True)


def detect_class_group(classes):
    """Detect which type of paragraph this is based on classes."""
    cls_lower = " ".join(c.lower() for c in classes)

    if "subtitles" in cls_lower:
        return "subtitles"
    if "section-header-page-break" in cls_lower:
        return "section_header"
    if "section-title" in cls_lower:
        return "section_title"
    if "chapter-header-page-break" in cls_lower:
        return "chapter_header"
    if "chapter-title" in cls_lower:
        return "chapter_title"
    if "quote-indented" in cls_lower:
        return "quote"
    if "footnote" in cls_lower:
        return "footnote"
    if "caption" in cls_lower:
        return "caption"
    if "bill-of-rights-bullets" in cls_lower or "article-rights-no-bullets" in cls_lower:
        return "rights_bullet"
    if "question-bullets" in cls_lower:
        return "question_bullet"
    if any(c in classes for c in BODY_CLASSES):
        return "body"

    return "unknown"


def collect_section_title(elements, start_idx):
    """Collect consecutive Section-Title paragraphs starting from start_idx.
    elements is a list of (tag_name, element) tuples.
    """
    titles = []
    i = start_idx
    while i < len(elements):
        tag_name, el = elements[i]
        if tag_name != "p":
            break
        classes = get_classes(el)
        if "Section-Title" not in classes and "Section-title" not in classes:
            break
        text = process_inline(el).strip()
        if text:
            titles.append(text)
        i += 1
    return titles, i - 1


def collect_chapter_title(elements, start_idx):
    """Collect consecutive Chapter-title paragraphs starting from start_idx.
    elements is a list of (tag_name, element) tuples.
    """
    titles = []
    i = start_idx
    while i < len(elements):
        tag_name, el = elements[i]
        if tag_name != "p":
            break
        classes = get_classes(el)
        if "Chapter-title" not in classes and "Chapter-title-Page-Break" not in classes:
            break
        text = process_inline(el).strip()
        if text:
            titles.append(text)
        i += 1
    return titles, i - 1


def convert_table(table):
    """Convert HTML table to GFM markdown table."""
    rows = table.find_all("tr")
    if not rows:
        return ""

    md_rows = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        md_cells = []
        for cell in cells:
            text = process_inline(cell).strip()
            md_cells.append(text)
        md_rows.append("| " + " | ".join(md_cells) + " |")

    if not md_rows:
        return ""

    # Add separator row
    num_cols = len(rows[0].find_all(["td", "th"]))
    separator = "| " + " | ".join(["---"] * num_cols) + " |"
    md_rows.insert(1, separator)

    return "\n".join(md_rows)


def flatten_body(body):
    """Flatten body into ordered list of elements, expanding divs."""
    elements = []
    for child in body.children:
        if isinstance(child, Tag):
            if child.name == "div":
                classes = get_classes(child)
                if "_idFootnotes" in classes:
                    elements.append(("footnotes_container", child))
                else:
                    # Regular div - expand its children
                    for sub in child.children:
                        if isinstance(sub, Tag):
                            if sub.name == "div":
                                sub_classes = get_classes(sub)
                                if "_idFootnotes" in sub_classes:
                                    elements.append(("footnotes_container", sub))
                                else:
                                    elements.append((sub.name, sub))
                            else:
                                elements.append((sub.name, sub))
            else:
                elements.append((child.name, child))
    return elements


def collect_footnotes(container):
    """Collect footnotes from a container div."""
    footnotes = {}
    for aside in container.find_all("aside", class_="_idFootnote"):
        fn_id = aside.get("id", "")
        if not fn_id:
            continue
        fn_p = aside.find("p", class_="Footnote")
        if fn_p:
            # Remove ALL empty anchor tags (backlinks and named anchors)
            for a_tag in fn_p.find_all("a"):
                if not a_tag.get_text(strip=True) and not a_tag.get("href"):
                    a_tag.decompose()
                elif a_tag.get("class") and any("Backlink" in str(c) or "Anchor" in str(c) for c in a_tag.get("class")):
                    a_tag.decompose()
                elif a_tag.get("epub:type") == "noteref" or not a_tag.get_text(strip=True):
                    a_tag.decompose()
            fn_text = process_inline(fn_p).strip()
            footnotes[fn_id] = fn_text
    return footnotes


def convert_file(xhtml_path, output_dir):
    """Convert a single XHTML file to markdown."""
    with open(xhtml_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml-xml")

    body = soup.find("body")
    if body is None:
        print(f"  WARNING: No body found in {xhtml_path.name}")
        return None

    elements = flatten_body(body)
    lines = []
    all_footnotes = {}

    i = 0
    while i < len(elements):
        tag_name, el = elements[i]

        if tag_name == "footnotes_container":
            fn_dict = collect_footnotes(el)
            all_footnotes.update(fn_dict)
            i += 1
            continue

        if tag_name == "p":
            classes = get_classes(el)
            group = detect_class_group(classes)

            if group == "section_header":
                header_text = el.get_text(strip=True)
                titles, last_idx = collect_section_title(elements, i + 1)
                i = last_idx
                # Replace newlines from <br/> with spaces in titles
                title_combined = " ".join(t.strip().replace("\n", " ") for t in titles)
                title_combined = " ".join(title_combined.split())  # collapse whitespace
                if title_combined:
                    line = f"# {header_text}: {title_combined}"
                else:
                    line = f"# {header_text}"
                lines.append(line)
                lines.append("")

            elif group == "chapter_header":
                header_text = el.get_text(strip=True)
                titles, last_idx = collect_chapter_title(elements, i + 1)
                i = last_idx
                # Replace newlines from <br/> with spaces in titles
                title_combined = " ".join(t.strip().replace("\n", " ") for t in titles)
                title_combined = " ".join(title_combined.split())  # collapse whitespace
                if title_combined:
                    line = f"## {header_text}: {title_combined}"
                else:
                    line = f"## {header_text}"
                lines.append(line)
                lines.append("")

            elif group == "subtitles":
                text = process_inline(el).strip()
                if text:
                    lines.append(f"### {text}")
                    lines.append("")

            elif group == "quote":
                text = process_inline(el).strip()
                if text:
                    for para_line in text.split("\n"):
                        lines.append(f"> {para_line}")
                    lines.append("")

            elif group == "caption":
                text = process_inline(el).strip()
                if text:
                    lines.append(f"*{text}*")
                    lines.append("")

            elif group in ("body", "unknown"):
                text = process_inline(el).strip()
                if text:
                    lines.append(text)
                    lines.append("")

            elif group == "rights_bullet":
                text = process_inline(el).strip()
                if text:
                    lines.append(f"- {text}")

            elif group == "question_bullet":
                text = process_inline(el).strip()
                if text:
                    lines.append(f"- {text}")

            else:
                text = process_inline(el).strip()
                if text:
                    lines.append(text)
                    lines.append("")

        elif tag_name == "ul":
            list_lines = []
            for li in el.find_all("li", recursive=False):
                text = process_inline(li).strip()
                if text:
                    list_lines.append(f"- {text}")
            if list_lines:
                lines.append("")
                lines.extend(list_lines)
                lines.append("")

        elif tag_name == "ol":
            list_lines = []
            for idx, li in enumerate(el.find_all("li", recursive=False), 1):
                text = process_inline(li).strip()
                if text:
                    list_lines.append(f"{idx}. {text}")
            if list_lines:
                lines.append("")
                lines.extend(list_lines)
                lines.append("")

        elif tag_name == "table":
            table_md = convert_table(el)
            if table_md:
                lines.append(table_md)
                lines.append("")

        else:
            pass  # Unknown element type

        i += 1

    # Append footnotes at the end
    if all_footnotes:
        lines.append("---")
        lines.append("")
        for fn_id, fn_text in all_footnotes.items():
            lines.append(f"[^{fn_id}]: {fn_text}")
        lines.append("")

    content = "\n".join(lines)

    # Write output
    output_filename = xhtml_path.stem + ".md"
    output_path = output_dir / output_filename
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


def main():
    script_dir = Path(__file__).parent
    input_dir = script_dir / INPUT_DIR
    output_dir = script_dir / OUTPUT_DIR

    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all XHTML files (excluding toc, cover, etc. frontmatter-only files)
    xhtml_files = sorted(input_dir.glob("World_Beyond_Monogamy_Final_eBook*.xhtml"))
    xhtml_files.append(input_dir / "Frontispiece.xhtml")

    print(f"Converting {len(xhtml_files)} files...")
    success_count = 0

    for xhtml_path in xhtml_files:
        if not xhtml_path.exists():
            print(f"  SKIP: {xhtml_path.name} (not found)")
            continue

        try:
            result = convert_file(xhtml_path, output_dir)
            if result:
                print(f"  OK: {xhtml_path.name} -> {result.name}")
                success_count += 1
            else:
                print(f"  SKIP: {xhtml_path.name}")
        except Exception as e:
            print(f"  FAIL: {xhtml_path.name} - {e}")

    print(f"\nDone. {success_count}/{len(xhtml_files)} files converted to {output_dir}/")


if __name__ == "__main__":
    main()
