#!/usr/bin/env python3
"""
build-chapter.py — Convert a translated .txt file into a chapter HTML page.

Usage:
    python build-chapter.py translated/NN-slug.txt

What it does:
    1. Parses the .txt file (handles 3-layer and 4-layer verse formats)
    2. Writes chapters/NN-slug.html with full nav buttons
    3. Updates chapters.html (coming-soon → available)
    4. Updates neighbouring chapter files (prev/next nav buttons)
"""

import re, sys
from pathlib import Path
from html import escape

BASE = Path(__file__).parent


# ── Helpers ──────────────────────────────────────────────────────────────────

def split_chunks(line):
    """Split a verse line on 4+ spaces into chunks."""
    return [c.strip() for c in re.split(r'    +', line.strip()) if c.strip()]

def chunks_to_html(chunks):
    return ' · '.join(escape(c) for c in chunks)


# ── Parse .txt ────────────────────────────────────────────────────────────────

def parse_txt(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    lines = text.splitlines()

    # Header (first 4 lines)
    # Line 0: "Tamil Title — ENGLISH TITLE"
    # Line 2: "By Manikkavasagar | Thiruvasagam, Chapter N"
    # Line 3: "Composed at <Location>"
    title_parts = lines[0].split(' — ', 1)
    tamil_title   = title_parts[0].strip()
    english_title = title_parts[1].strip().title() if len(title_parts) > 1 else title_parts[0].strip().title()

    ch_match  = re.search(r'Chapter\s+(\d+)', lines[2])
    chapter_num = int(ch_match.group(1)) if ch_match else 0

    loc_match = re.search(r'Composed at (.+)', lines[3])
    location  = loc_match.group(1).strip() if loc_match else ''

    # Split body on separator lines (━━━…)
    SEP = re.compile(r'^━{10,}')
    sep_pos = [i for i, l in enumerate(lines) if SEP.match(l.strip())]

    verses = []

    for idx, sep_start in enumerate(sep_pos):
        block_start = sep_start + 1
        block_end   = sep_pos[idx + 1] if idx + 1 < len(sep_pos) else len(lines)
        block = lines[block_start:block_end]

        # Strip blank edges
        while block and not block[0].strip():  block.pop(0)
        while block and not block[-1].strip(): block.pop()
        if not block:
            continue

        # Skip closing Tiruchitrambalam block
        if any('திருச்சிற்றம்பலம்' in l or 'TIRUCHITRAMBALAM' in l for l in block):
            continue

        # First non-blank line = verse number
        if not block[0].strip().isdigit():
            continue
        verse_num = int(block[0].strip())

        # Remaining content
        rest = block[1:]
        while rest and not rest[0].strip():
            rest.pop(0)

        # Find start of English translation (**…)
        eng_start = next((i for i, l in enumerate(rest) if l.strip().startswith('**')), None)
        if eng_start is None:
            continue

        content_lines = [l for l in rest[:eng_start] if l.strip()]
        eng_raw = [l.strip() for l in rest[eng_start:] if l.strip()]

        # Strip ** markers from English block
        if eng_raw:
            eng_raw[0]  = eng_raw[0].lstrip('*').strip()
            eng_raw[-1] = eng_raw[-1].rstrip('*').strip()
            eng_raw = [l for l in eng_raw if l]

        # Determine layers by count of content lines
        if len(content_lines) >= 3:
            tamil_line, translit_line, gloss_line = content_lines[0], content_lines[1], content_lines[2]
        elif len(content_lines) == 2:
            tamil_line, translit_line, gloss_line = content_lines[0], None, content_lines[1]
        elif len(content_lines) == 1:
            tamil_line, translit_line, gloss_line = content_lines[0], None, None
        else:
            continue

        verses.append({
            'num':     verse_num,
            'tamil':   tamil_line,
            'translit': translit_line,
            'gloss':   gloss_line,
            'english': eng_raw,
        })

    return {
        'tamil_title':   tamil_title,
        'english_title': english_title,
        'chapter_num':   chapter_num,
        'location':      location,
        'verses':        verses,
    }


# ── Nav ───────────────────────────────────────────────────────────────────────

def get_available_chapters(new_num=None, new_slug=None):
    """Return sorted (num, slug) list of existing chapter HTML files,
    optionally including a new chapter being added."""
    chapters_dir = BASE / 'chapters'
    result = {}
    for f in chapters_dir.glob('*.html'):
        m = re.match(r'^(\d+)-', f.stem)
        if m:
            result[int(m.group(1))] = f.stem
    if new_num is not None:
        result[new_num] = new_slug
    return sorted(result.items())


def get_nav_neighbours(chapter_num, slug):
    available = get_available_chapters(chapter_num, slug)
    pos = next((i for i, (n, _) in enumerate(available) if n == chapter_num), None)
    if pos is None:
        return None, None, None, None
    prev_num, prev_slug = available[pos - 1] if pos > 0 else (None, None)
    next_num, next_slug = available[pos + 1] if pos < len(available) - 1 else (None, None)
    return prev_slug, prev_num, next_slug, next_num


def make_nav_html(prev_slug, prev_num, next_slug, next_num):
    prev_btn = (f'<a href="{prev_slug}.html" class="nav-btn">← Ch. {prev_num}</a>'
                if prev_slug else '<span class="nav-btn nav-disabled"></span>')
    next_btn = (f'<a href="{next_slug}.html" class="nav-btn">Ch. {next_num} →</a>'
                if next_slug else '<span class="nav-btn nav-disabled"></span>')
    return (
        '    <div class="chapter-nav">\n'
        f'      {prev_btn}\n'
        '      <a href="../chapters.html" class="nav-btn nav-home">All Chapters</a>\n'
        f'      {next_btn}\n'
        '    </div>'
    )


# ── Build HTML ────────────────────────────────────────────────────────────────

def build_verse_html(verse):
    n = verse['num']
    parts = [
        f'    <article class="verse" id="verse-{n}">',
        f'      <div class="verse-number">{n}</div>',
        f'      <p class="tamil">{chunks_to_html(split_chunks(verse["tamil"]))}</p>',
    ]
    if verse['translit']:
        parts.append(f'      <p class="translit">{chunks_to_html(split_chunks(verse["translit"]))}</p>')
    if verse['gloss']:
        parts.append(f'      <p class="gloss">{chunks_to_html(split_chunks(verse["gloss"]))}</p>')
    eng = '<br>\n        '.join(escape(l) for l in verse['english'])
    parts += [f'      <blockquote>{eng}</blockquote>', '    </article>']
    return '\n'.join(parts)


def build_html(data, slug):
    prev_slug, prev_num, next_slug, next_num = get_nav_neighbours(data['chapter_num'], slug)
    nav = make_nav_html(prev_slug, prev_num, next_slug, next_num)
    verses_html = '\n\n'.join(build_verse_html(v) for v in data['verses'])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escape(data['english_title'])} · Thiruvasagam</title>
  <link rel="stylesheet" href="../style.css" />
</head>
<body>

  <nav>
    <span class="site-title">திருவாசகம் · Thiruvasagam</span>
    <a href="../index.html">Home</a>
    <a href="../chapters.html">Chapters</a>
    <a href="../locations.html">Locations</a>
    <a href="../siva-names.html">Siva Names</a>
    <a href="../Reference.html">Reference</a>
  </nav>

  <div class="container">

    <div class="chapter-header">
      <h1>{escape(data['english_title'])}</h1>
      <div class="tamil-title">{escape(data['tamil_title'])}</div>
      <div class="meta">Chapter {data['chapter_num']} · Composed at {escape(data['location'])}</div>
    </div>

{nav}

{verses_html}

    <p style="text-align:center; margin-top: 3rem; color: #888;">திருச்சிற்றம்பலம் · Tiruchitrambalam</p>

{nav}

  </div>

  <footer>
    திருச்சிற்றம்பலம் · Tiruchitrambalam
  </footer>

</body>
</html>"""


# ── Update chapters.html ──────────────────────────────────────────────────────

def update_chapters_html(chapter_num, slug):
    filepath = BASE / 'chapters.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    num_str = str(chapter_num).zfill(2)

    pattern = re.compile(
        r'<div class="chapter-card coming-soon">\s*\n'
        r'(\s*<div class="num">0?' + str(chapter_num) + r'</div>\s*\n)'
        r'(\s*<div class="name">.*?</div>\s*\n)'
        r'(\s*<div class="verse-count">.*?</div>\s*\n)'
        r'(\s*<div class="theme">.*?</div>\s*\n)'
        r'\s*</div>',
        re.MULTILINE
    )

    def replacer(m):
        return (
            f'<a href="chapters/{slug}.html" class="chapter-card available">\n'
            + m.group(1) + m.group(2) + m.group(3) + m.group(4)
            + '        </a>'
        )

    new_content, count = pattern.subn(replacer, content, count=1)
    if count == 0:
        print(f"  WARN:Could not find coming-soon card for chapter {chapter_num} in chapters.html")
        return

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"  OK:chapters.html: chapter {chapter_num} marked available")


# ── Update neighbouring chapter nav buttons ───────────────────────────────────

def update_neighbour_nav(slug, chapter_num, prev_slug, prev_num, next_slug, next_num):
    chapters_dir = BASE / 'chapters'

    # Update prev chapter's NEXT button (comes after "All Chapters" link)
    if prev_slug:
        path = chapters_dir / f"{prev_slug}.html"
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            new_btn = f'<a href="{slug}.html" class="nav-btn">Ch. {chapter_num} →</a>'
            content = re.sub(
                r'(All Chapters</a>\s*\n\s*)(?:<a href="[^"]*" class="nav-btn">Ch\. \d+ →</a>|<span class="nav-btn nav-disabled"></span>)',
                r'\1' + new_btn,
                content
            )
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  OK:{prev_slug}.html: next -> Ch. {chapter_num}")

    # Update next chapter's PREV button (comes before "All Chapters" link)
    if next_slug:
        path = chapters_dir / f"{next_slug}.html"
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            new_btn = f'<a href="{slug}.html" class="nav-btn">← Ch. {chapter_num}</a>'
            content = re.sub(
                r'(?:<a href="[^"]*" class="nav-btn">← Ch\. \d+</a>|<span class="nav-btn nav-disabled"></span>)(\s*\n\s*<a href="\.\.\/chapters\.html")',
                new_btn + r'\1',
                content
            )
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  OK:{next_slug}.html: prev -> Ch. {chapter_num}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python build-chapter.py translated/NN-slug.txt")
        sys.exit(1)

    txt_path = Path(sys.argv[1])
    if not txt_path.is_absolute():
        txt_path = BASE / txt_path
    if not txt_path.exists():
        print(f"Error: {txt_path} not found")
        sys.exit(1)

    slug = txt_path.stem

    print(f"\nParsing {txt_path.name} ...")
    data = parse_txt(txt_path)
    print(f"  Chapter {data['chapter_num']}: {data['english_title']} ({len(data['verses'])} verses)")

    prev_slug, prev_num, next_slug, next_num = get_nav_neighbours(data['chapter_num'], slug)
    print(f"  Nav: prev={prev_slug} ({prev_num})  next={next_slug} ({next_num})")

    # Write HTML
    html = build_html(data, slug)
    out_path = BASE / 'chapters' / f"{slug}.html"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  OK:Written: chapters/{slug}.html")

    # Update chapters.html
    update_chapters_html(data['chapter_num'], slug)

    # Update neighbours
    update_neighbour_nav(slug, data['chapter_num'], prev_slug, prev_num, next_slug, next_num)

    print(f"\nDone. To publish:")
    print(f"  git add -u && git add chapters/{slug}.html")
    print(f'  git commit -m "Add chapter {data["chapter_num"]}: {data["english_title"]}"')
    print(f"  git push")


if __name__ == '__main__':
    main()
