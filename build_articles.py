#!/usr/bin/env python3
"""Convert Notion Markdown exports to articles.js for FOMUS archive site."""

import os
import re
import json
import html
import glob
import urllib.parse

BASE = "/Users/masuo/Downloads/海外活動記録の全て/セブ島/まっすー セブ島 活動記"
OUT = "/Users/masuo/Downloads/海外活動記録の全て/output"


def inline_format(text):
    """Apply inline Markdown formatting."""
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


def fix_image_path(src):
    """Fix image paths to point to output/images/ directory."""
    decoded = urllib.parse.unquote(src)
    parts = decoded.split('/')
    if len(parts) >= 2:
        folder_name = parts[-2]
        filename = parts[-1]
        return f'./images/{urllib.parse.quote(folder_name)}/{urllib.parse.quote(filename)}'
    else:
        filename = parts[-1]
        return f'./images/{urllib.parse.quote(filename)}'


def md_to_html(md_text):
    """Convert Markdown text to HTML."""
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

        # Headings
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

        # Images: ![alt](path)
        img_match = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)$', stripped)
        if img_match:
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
                list_type = None
            alt = html.escape(img_match.group(1))
            src = fix_image_path(img_match.group(2))
            html_parts.append(f'<div class="article-image"><img src="{src}" alt="{alt}" loading="lazy"></div>')
            continue

        # Unordered list
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

        # Ordered list
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

        # Blockquote
        if stripped.startswith('>'):
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
                list_type = None
            quote_text = inline_format(stripped[1:].strip())
            html_parts.append(f'<blockquote>{quote_text}</blockquote>')
            continue

        # Horizontal rule (Japanese dash or standard)
        if re.match(r'^[-ー━─=]{3,}$', stripped):
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
                list_type = None
            html_parts.append('<hr>')
            continue

        # Regular paragraph
        if in_list:
            html_parts.append(f'</{list_type}>')
            in_list = False
            list_type = None

        # Check for inline image within paragraph
        if re.match(r'!\[', stripped):
            img_inline = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)(.*)$', stripped)
            if img_inline:
                alt = html.escape(img_inline.group(1))
                src = fix_image_path(img_inline.group(2))
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


def main():
    md_files = glob.glob(os.path.join(BASE, "*.md"))
    articles = []

    for md_path in md_files:
        fname = os.path.basename(md_path)

        # Extract article number: "1 自己紹介と目的 8cb1d49a....md"
        match = re.match(r'^(\d+)\s+(.+?)\s+[0-9a-f]{20,}\.md$', fname)
        if not match:
            print(f"Skipping: {fname}")
            continue

        num = int(match.group(1))
        title_from_filename = match.group(2)

        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove date line if present (e.g., "2024/04/30")
        content = re.sub(r'^\d{4}/\d{2}/\d{2}\s*$', '', content, flags=re.MULTILINE)

        # Extract title from first heading
        title_match = re.match(r'^#\s*\d*[:：]?\s*(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            content = content[title_match.end():].strip()
        else:
            title = title_from_filename

        # Category
        if num in [86, 87, 88, 89]:
            category = 'manila'
        elif num in [56, 57, 58]:
            category = 'zamboanga'
        elif 'マニラ' in title:
            category = 'manila'
        elif 'ザンボアンガ' in title:
            category = 'zamboanga'
        else:
            category = 'cebu'

        body_html = md_to_html(content)

        # Excerpt
        plain = re.sub(r'<[^>]+>', '', body_html)
        plain = re.sub(r'\s+', ' ', plain).strip()
        excerpt = plain[:100]

        articles.append({
            'id': num,
            'num': f'{num:03d}',
            'title': title,
            'category': category,
            'excerpt': excerpt,
            'body': body_html
        })

    # Sort by id
    articles.sort(key=lambda a: a['id'])

    # Output as JavaScript
    js_content = "const articles = " + json.dumps(articles, ensure_ascii=False, indent=2) + ";\n"

    os.makedirs(OUT, exist_ok=True)
    output_path = os.path.join(OUT, "articles.js")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"Generated {len(articles)} articles -> {output_path}")
    for a in articles:
        print(f"  [{a['num']}] {a['title']} ({a['category']})")


if __name__ == '__main__':
    main()
