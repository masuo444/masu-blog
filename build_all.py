#!/usr/bin/env python3
"""Convert all Notion Markdown exports to articles.js for FOMUS archive site."""

import os
import re
import json
import html
import glob
import shutil
import urllib.parse

ROOT = "/Users/masuo/Downloads/海外活動記録の全て"
OUT = os.path.join(ROOT, "output")
IMAGES_OUT = os.path.join(OUT, "images")

# Define all source folders with their category info
# (parent_folder, subfolder, category_key, category_label, id_offset)
SOURCES = [
    ("セブ島", "まっすー セブ島 活動記", "cebu", "セブ島", 0),
    ("マレーシア", "まっすー マレーシア活動記", "malaysia", "マレーシア", 0),
    ("アイルランド", "アイルランド活動記🇮🇪", "ireland", "アイルランド", 0),
    ("アメリカスペイン", "アメリカ・スペイン活動記🇺🇸🇪🇸", "us_spain", "アメリカ・スペイン", 0),
    ("ヨーロッパ２", "ヨーロッパ活動記②", "europe2", "ヨーロッパ②", 0),
    ("ヨーロッパ３", "ヨーロッパ活動記③", "europe3", "ヨーロッパ③", 0),
    ("ヨーロッパ４", "ヨーロッパ活動記④ castle篇", "europe4", "ヨーロッパ④", 0),
]


def inline_format(text):
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)

    def fix_link(m):
        link_text = m.group(1)
        url = html.unescape(m.group(2))
        if url.startswith('http://') or url.startswith('https://'):
            return f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{link_text}</a>'
        return link_text

    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', fix_link, text)
    return text


def fix_image_path(src, category_key):
    # Keep external URLs as-is
    if src.startswith('http://') or src.startswith('https://'):
        return src
    decoded = urllib.parse.unquote(src)
    parts = decoded.split('/')
    if len(parts) >= 2:
        folder_name = parts[-2]
        filename = parts[-1]
        return f'./images/{category_key}/{urllib.parse.quote(folder_name)}/{urllib.parse.quote(filename)}'
    else:
        filename = parts[-1]
        return f'./images/{category_key}/{urllib.parse.quote(filename)}'


def md_to_html(md_text, category_key):
    lines = md_text.split('\n')
    html_parts = []
    in_list = False
    list_type = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
                list_type = None
            continue

        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
                list_type = None
            level = len(heading_match.group(1))
            text = inline_format(heading_match.group(2))
            html_parts.append(f'<h{level}>{text}</h{level}>')
            continue

        img_match = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)$', stripped)
        if img_match:
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
                list_type = None
            alt = html.escape(img_match.group(1))
            src = fix_image_path(img_match.group(2), category_key)
            html_parts.append(f'<div class="article-image"><img src="{src}" alt="{alt}" loading="lazy"></div>')
            continue

        ul_match = re.match(r'^[-*]\s+(.+)$', stripped)
        if ul_match:
            if not in_list or list_type != 'ul':
                if in_list:
                    html_parts.append(f'</{list_type}>')
                html_parts.append('<ul>')
                in_list = True
                list_type = 'ul'
            text = inline_format(ul_match.group(1))
            html_parts.append(f'<li>{text}</li>')
            continue

        ol_match = re.match(r'^\d+\.\s+(.+)$', stripped)
        if ol_match:
            if not in_list or list_type != 'ol':
                if in_list:
                    html_parts.append(f'</{list_type}>')
                html_parts.append('<ol>')
                in_list = True
                list_type = 'ol'
            text = inline_format(ol_match.group(1))
            html_parts.append(f'<li>{text}</li>')
            continue

        if stripped.startswith('>'):
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
                list_type = None
            quote_text = inline_format(stripped[1:].strip())
            html_parts.append(f'<blockquote>{quote_text}</blockquote>')
            continue

        if re.match(r'^[-ー━─=]{3,}$', stripped):
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
                list_type = None
            html_parts.append('<hr>')
            continue

        if in_list:
            html_parts.append(f'</{list_type}>')
            in_list = False
            list_type = None

        if re.match(r'^!\[', stripped):
            img_inline = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)(.*)$', stripped)
            if img_inline:
                alt = html.escape(img_inline.group(1))
                src = fix_image_path(img_inline.group(2), category_key)
                rest = img_inline.group(3).strip()
                html_parts.append(f'<div class="article-image"><img src="{src}" alt="{alt}" loading="lazy"></div>')
                if rest:
                    html_parts.append(f'<p>{inline_format(rest)}</p>')
                continue

        text = inline_format(stripped)
        html_parts.append(f'<p>{text}</p>')

    if in_list:
        html_parts.append(f'</{list_type}>')

    return '\n'.join(html_parts)


def extract_sort_key(fname):
    """Extract a numeric sort key from filename."""
    import unicodedata
    nf = unicodedata.normalize('NFC', fname)

    m = re.match(r'^(\d+)\s+', nf)
    if m:
        return (int(m.group(1)), fname)

    m = re.match(r'^【(\d+)日目】', nf)
    if m:
        return (int(m.group(1)), fname)

    m = re.match(r'^【番外編(\d*)】', nf)
    if m:
        num = int(m.group(1)) if m.group(1) else 999
        return (9000 + num, fname)

    if nf.startswith('プロローグ') or nf.startswith('はじめに'):
        return (0, fname)

    return (5000, fname)


def extract_title(content, fname):
    """Extract title from content or filename."""
    title_match = re.match(r'^#\s*(.+)$', content, re.MULTILINE)
    if title_match:
        raw = title_match.group(1).strip()
        # Remove leading number patterns like "1:" or "90:"
        raw = re.sub(r'^\d+[:：]\s*', '', raw)
        return raw, content[title_match.end():].strip()

    # Fallback: derive from filename
    # Remove hash and .md
    m = re.match(r'^(.+?)\s+[0-9a-f]{20,}\.md$', fname)
    if m:
        return m.group(1).strip(), content
    return fname.replace('.md', ''), content


def extract_date(content):
    """Extract date from content."""
    m = re.search(r'(\d{4}/\d{2}/\d{2})', content[:500])
    if m:
        return m.group(1).replace('/', '.')
    return ''


def copy_images(base_dir, category_key):
    """Copy image directories to output."""
    dest_base = os.path.join(IMAGES_OUT, category_key)
    os.makedirs(dest_base, exist_ok=True)

    copied = 0
    for d in os.listdir(base_dir):
        src_dir = os.path.join(base_dir, d)
        if not os.path.isdir(src_dir):
            continue

        has_images = False
        for ext in ['*.jpeg', '*.jpg', '*.png', '*.webp', '*.gif']:
            if glob.glob(os.path.join(src_dir, ext)):
                has_images = True
                break

        if has_images:
            dest_dir = os.path.join(dest_base, d)
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            shutil.copytree(src_dir, dest_dir)
            copied += 1

    return copied


def process_source(parent_folder, subfolder, category_key, category_label, id_offset):
    """Process one source folder and return list of articles."""
    base = os.path.join(ROOT, parent_folder, subfolder)
    if not os.path.exists(base):
        print(f"WARNING: {base} not found, skipping")
        return []

    # Copy images
    img_dirs = copy_images(base, category_key)

    # Find all MD files
    md_files = glob.glob(os.path.join(base, "*.md"))

    articles = []
    for md_path in md_files:
        fname = os.path.basename(md_path)

        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        sort_key = extract_sort_key(fname)
        title, body_content = extract_title(content, fname)

        # Remove date line from body
        body_content = re.sub(r'^\d{4}/\d{2}/\d{2}\s*$', '', body_content, flags=re.MULTILINE).strip()

        date = extract_date(content)
        body_html = md_to_html(body_content, category_key)

        # Extract thumbnail
        imgs = re.findall(r'<img\s+src="([^"]+)"', body_html)
        thumbnail = imgs[0] if imgs else ''

        # Excerpt
        plain = re.sub(r'<[^>]+>', '', body_html)
        plain = re.sub(r'\s+', ' ', plain).strip()
        excerpt = plain[:100]

        articles.append({
            'sort_key': sort_key,
            'title': title,
            'category': category_key,
            'date': date,
            'excerpt': excerpt,
            'body': body_html,
            'thumbnail': thumbnail,
        })

    # Sort by extracted key
    articles.sort(key=lambda a: a['sort_key'])

    print(f"  {category_label}: {len(articles)} articles, {img_dirs} image dirs")
    return articles


EN_FIELDS = ('title_en', 'excerpt_en', 'body_en', 'country_en')


def load_existing_translations(path):
    """Load existing English translation fields from articles.js, keyed by id."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        json_str = content.replace('const articles = ', '', 1).rstrip(';\n')
        existing = json.loads(json_str)
        translations = {}
        for a in existing:
            en_data = {k: a[k] for k in EN_FIELDS if k in a}
            if en_data:
                translations[a['id']] = en_data
        return translations
    except Exception as e:
        print(f"WARNING: Could not load existing translations: {e}")
        return {}


def main():
    os.makedirs(IMAGES_OUT, exist_ok=True)

    # Load existing English translations before rebuild
    output_path = os.path.join(OUT, "articles.js")
    existing_en = load_existing_translations(output_path)
    if existing_en:
        print(f"Loaded existing English translations for {len(existing_en)} articles")

    all_articles = []
    global_id = 0

    for parent_folder, subfolder, cat_key, cat_label, offset in SOURCES:
        print(f"Processing: {cat_label} ({parent_folder}/{subfolder})")
        arts = process_source(parent_folder, subfolder, cat_key, cat_label, offset)

        for a in arts:
            global_id += 1
            a['id'] = global_id
            a['num'] = f'{global_id:03d}'
            del a['sort_key']

        all_articles.extend(arts)

    # Merge existing English translations back
    merged = 0
    for a in all_articles:
        if a['id'] in existing_en:
            a.update(existing_en[a['id']])
            merged += 1
    if merged:
        print(f"Merged English translations for {merged} articles")

    # Output
    js_content = "const articles = " + json.dumps(all_articles, ensure_ascii=False, indent=2) + ";\n"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"\n=== TOTAL: {len(all_articles)} articles ===")

    # Summary by category
    cats = {}
    for a in all_articles:
        cats[a['category']] = cats.get(a['category'], 0) + 1
    for k, v in cats.items():
        print(f"  {k}: {v}")

    # Count with thumbnails
    with_thumb = sum(1 for a in all_articles if a['thumbnail'])
    print(f"  Thumbnails: {with_thumb}/{len(all_articles)}")

    # Count with dates
    with_date = sum(1 for a in all_articles if a['date'])
    print(f"  Dates: {with_date}/{len(all_articles)}")


if __name__ == '__main__':
    main()
