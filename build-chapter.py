#!/usr/bin/env python3
"""
build-chapter.py — Convert a translated .txt file into a chapter HTML page.

Usage:
    python build-chapter.py translated/NN-slug.txt

What it does:
    1. Parses the .txt file (4-layer format: Tamil / Translit / Gloss / English)
    2. Writes chapters/NN-slug.html with summary, full nav buttons
    3. Updates chapters.html (coming-soon → available)
    4. Updates neighbouring chapter files (prev/next nav buttons)

.txt format:
    Tamil Title — ENGLISH TITLE
    ====================================
    By Manikkavasagar | Thiruvasagam, Chapter N
    Composed at <Location>

    [Summary paragraph — any text here before the first separator]

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    1

    Tamil    chunks    here
    Translit    chunks    here
    Gloss    chunks    here

    **English translation**
"""

import re, sys
from pathlib import Path
from html import escape

BASE = Path(__file__).parent

CHAPTER_SLUGS = {
    1:  "01-sivapuranam",
    2:  "02-kirttit-tiru-agaval",
    3:  "03-tiru-andap-pakuti",
    4:  "04-porrrit-tiru-agaval",
    5:  "05-tiru-ccatakam",
    6:  "06-neettal-vinnappam",
    7:  "07-tiru-empavai",
    8:  "08-tiru-ammanai",
    9:  "09-tiru-porr-cunnam",
    10: "10-tiru-kottumpi",
    11: "11-tiru-tellenam",
    12: "12-tiru-ccazal",
    13: "13-tiru-puvalli",
    14: "14-tiru-untiyar",
    15: "15-tiru-tol-nokkam",
    16: "16-tiru-ponnusal",
    17: "17-annai-pattu",
    18: "18-kuyil-pattu",
    19: "19-tiru-tacankam",
    20: "20-tiru-palliyezhucchi",
    21: "21-koyil-mutta-tiruppatikam",
    22: "22-koyil-tiruppatikam",
    23: "23-cettilap-pattu",
    24: "24-ataikkala-pattu",
    25: "25-acai-pattu",
    26: "26-aticiya-pattu",
    27: "27-punarcchi-pattu",
    28: "28-valap-pattu",
    29: "29-arut-pattu",
    30: "30-tiru-kazukkunnra-patikam",
    31: "31-kanda-pattu",
    32: "32-pirartanai-pattu",
    33: "33-kuzaitta-pattu",
    34: "34-uyirunni-pattu",
    35: "35-acca-pattu",
    36: "36-tirupandi-patikam",
    37: "37-piditta-pattu",
    38: "38-tiru-ecaravu",
    39: "39-tiru-pulampal",
    40: "40-kulap-pattu",
    41: "41-arrputa-pattu",
    42: "42-cenni-pattu",
    43: "43-tiru-vartai",
    44: "44-enna-patikam",
    45: "45-yattirai-pattu",
    46: "46-tirupadai-ezhucchi",
    47: "47-tiru-venpa",
    48: "48-pantaya-nanmarai",
    49: "49-tirupadai-atci",
    50: "50-ananta-malai",
    51: "51-acco-patikam",
}


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

    # Summary: any non-blank text between line 4 and the first separator
    summary = ''
    if sep_pos:
        summary_lines = [l.strip() for l in lines[4:sep_pos[0]] if l.strip()]
        summary = ' '.join(summary_lines)

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

        # Determine layers — always expect 4-layer (Tamil / Translit / Gloss / English)
        if len(content_lines) >= 3:
            tamil_line, translit_line, gloss_line = content_lines[0], content_lines[1], content_lines[2]
        elif len(content_lines) == 2:
            # Old 3-layer format: Tamil + Gloss, no translit
            tamil_line, translit_line, gloss_line = content_lines[0], None, content_lines[1]
            print(f"  WARN: verse {verse_num} missing transliteration (3-layer format)")
        elif len(content_lines) == 1:
            tamil_line, translit_line, gloss_line = content_lines[0], None, None
            print(f"  WARN: verse {verse_num} missing transliteration and gloss")
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
        'summary':       summary,
        'verses':        verses,
    }


# ── Nav ───────────────────────────────────────────────────────────────────────

def get_nav_neighbours(chapter_num):
    prev_num = chapter_num - 1
    next_num = chapter_num + 1
    prev_slug = CHAPTER_SLUGS.get(prev_num)
    next_slug = CHAPTER_SLUGS.get(next_num)
    return (prev_slug, prev_num if prev_slug else None,
            next_slug, next_num if next_slug else None)


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
    prev_slug, prev_num, next_slug, next_num = get_nav_neighbours(data['chapter_num'])
    nav = make_nav_html(prev_slug, prev_num, next_slug, next_num)
    verses_html = '\n\n'.join(build_verse_html(v) for v in data['verses'])
    summary_html = (f'\n    <p class="chapter-summary">{escape(data["summary"])}</p>\n'
                    if data.get('summary') else '')

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
{summary_html}
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

    prev_slug, prev_num, next_slug, next_num = get_nav_neighbours(data['chapter_num'])
    print(f"  Nav: prev={prev_slug} ({prev_num})  next={next_slug} ({next_num})")

    # Write HTML
    html = build_html(data, slug)
    out_path = BASE / 'chapters' / f"{slug}.html"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  OK:Written: chapters/{slug}.html")

    # Update chapters.html
    update_chapters_html(data['chapter_num'], slug)

    print(f"\nDone. To publish:")
    print(f"  git add -u && git add chapters/{slug}.html")
    print(f'  git commit -m "Add chapter {data["chapter_num"]}: {data["english_title"]}"')
    print(f"  git push")


if __name__ == '__main__':
    main()
