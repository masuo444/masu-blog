#!/usr/bin/env python3
"""
sync_note.py — note.com の記事を FOMUS Archive に自動同期するスクリプト

使い方:
  python3 sync_note.py

動作:
  1. note.com API から kei_masu の全記事を取得
  2. 海外遠征記（中東遠征記など）を検出 → articles.js に追加
  3. 既存記事との重複を除外
  4. セブ島活動記・既に活動記に入っている記事をnoteから除外
  5. note_articles.js を再生成
"""

import os
import re
import json
import ssl
import time
import urllib.request
import urllib.error
import subprocess

# SSL context — certifi があれば使い、なければシステムデフォルト
try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")

NOTE_USER = "kei_masu"
NOTE_API_LIST = f"https://note.com/api/v2/creators/{NOTE_USER}/contents?kind=note&page={{page}}"
NOTE_API_DETAIL = "https://note.com/api/v3/notes/{key}"

# ============================================================
# 海外遠征記として活動記録に取り込むシリーズのキーワード
# 新しいシリーズが始まったらここに追加する
# ============================================================
EXPEDITION_SERIES = [
    "中東遠征記",
    "シンガポール遠征記",
    "台湾一周", "台湾プロジェクト", "台湾と枡",
    # 今後追加例: "南米遠征記", "アフリカ遠征記" etc.
]

# 遠征記シリーズごとのカテゴリ
EXPEDITION_CATEGORY = {
    "中東遠征記": "mideast",
    "シンガポール遠征記": "singapore",
    "台湾一周": "taiwan",
    "台湾プロジェクト": "taiwan",
    "台湾と枡": "taiwan",
}

# noteから除外するシリーズ（活動記録と完全重複）
EXCLUDE_FROM_NOTE = [
    "セブ島 活動記",
    "セブ島活動記",
]

# 国の自動判定ルール（タイトルキーワード → 国名）
COUNTRY_RULES = {
    'バーレーン': ['バーレーン'],
    'サウジアラビア': ['サウジ', 'リヤド', 'ディルイーヤ', 'ジェッダ'],
    'ドバイ(UAE)': ['ドバイ', 'アブダビ', 'UAE', 'デイラ', 'シャルジャ'],
    'カタール': ['カタール', 'ドーハ'],
    'オマーン': ['オマーン', 'マスカット'],
    'アイルランド': ['アイルランド', 'ダブリン', 'タラモア', 'ゴールウェイ'],
    'フランス': ['フランス', 'パリ', 'ボルドー'],
    'スペイン': ['スペイン', 'バルセロナ', 'マドリード'],
    'アメリカ': ['アメリカ', 'ニューヨーク', 'ロサンゼルス'],
    'フィリピン': ['セブ', 'マニラ', 'フィリピン'],
    'マレーシア': ['マレーシア', 'クアラルンプール'],
    'イギリス': ['イギリス', 'ロンドン'],
    'ドイツ': ['ドイツ', 'ベルリン', 'ミュンヘン'],
    'イタリア': ['イタリア', 'ローマ', 'ミラノ'],
    'ベルギー': ['ベルギー', 'ブリュッセル'],
    'ルーマニア': ['ルーマニア', 'ブカレスト'],
    '台湾': ['台湾', '台北', '高雄'],
    'シンガポール': ['シンガポール'],
}

# 国旗コード（新しい国が増えたら追加）
FLAG_CODES_NEW = {
    'バーレーン': 'bh',
    'サウジアラビア': 'sa',
    'カタール': 'qa',
    'オマーン': 'om',
    'シンガポール': 'sg',
}


def fetch_json(url, retries=3):
    """Fetch JSON from URL with retries."""
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if i == retries - 1:
                print(f"  ERROR fetching {url}: {e}")
                return None
            time.sleep(1)


def fetch_all_note_articles():
    """Fetch all articles from note.com API."""
    all_articles = []
    page = 1
    while True:
        url = NOTE_API_LIST.format(page=page)
        data = fetch_json(url)
        if not data:
            break

        contents = data.get('data', {}).get('contents', [])
        if not contents:
            break

        for c in contents:
            note_url = c.get('noteUrl', '') or c.get('note_url', '')
            key = c.get('key', '')
            if not key and note_url:
                key = note_url.rstrip('/').split('/')[-1]

            raw_date = c.get('publishAt', '') or c.get('publish_at', '') or c.get('createdAt', '') or c.get('created_at', '')
            all_articles.append({
                'title': c.get('name', ''),
                'url': note_url,
                'note_key': key,
                'date': raw_date[:10],
                'eyecatch': c.get('eyecatch', '') or '',
                'is_paid': c.get('isLimited', False) or c.get('is_limited', False) or (c.get('price', 0) > 0),
                'excerpt': (c.get('body', '') or '')[:200].strip(),
            })

        is_last = data.get('data', {}).get('isLastPage', False)
        if is_last:
            break
        page += 1
        time.sleep(0.3)

    print(f"Fetched {len(all_articles)} articles from note.com")
    return all_articles


def fetch_article_body(note_key):
    """Fetch full article body HTML from note API."""
    url = NOTE_API_DETAIL.format(key=note_key)
    data = fetch_json(url)
    if not data:
        return ''
    return data.get('data', {}).get('body', '') or ''


def normalize_title(t):
    """Normalize title for duplicate detection."""
    t = re.sub(r'[\s\u3000]+', '', t)
    t = re.sub(r'[【】「」『』（）()！!？?・、。,.:：]', '', t)
    return t.lower().strip()


def extract_day_key(title):
    """Extract series+day key for duplicate detection (e.g. '中東遠征記_day1')."""
    for series in EXPEDITION_SERIES:
        if series in title:
            m = re.search(r'[Dd]ay\s*(\d+)', title)
            if m:
                return f"{series}_day{m.group(1)}"
    return None


def detect_country(title):
    """Detect country from title keywords."""
    for country, keywords in COUNTRY_RULES.items():
        for kw in keywords:
            if kw in title:
                return country
    return ''


def is_expedition(title):
    """Check if article belongs to an expedition series."""
    for series in EXPEDITION_SERIES:
        if series in title:
            return True
    return False


def detect_expedition_category(title):
    """Detect category for expedition series (default: mideast)."""
    for series, category in EXPEDITION_CATEGORY.items():
        if series in title:
            return category
    return "mideast"


def is_excluded_from_note(title):
    """Check if article should be excluded from note list."""
    for pattern in EXCLUDE_FROM_NOTE:
        if pattern in title:
            return True
    return False


def main():
    print("=== FOMUS Archive Note Sync ===\n")

    # 1. Load existing archive
    articles_path = os.path.join(OUT, "articles.js")
    with open(articles_path, 'r') as f:
        content = f.read()
        archive = json.loads(content.replace('const articles = ', '').rstrip(';\n'))
    print(f"Existing archive: {len(archive)} articles")

    archive_titles = set(normalize_title(a['title']) for a in archive)
    archive_day_keys = set()
    for a in archive:
        dk = extract_day_key(a['title'])
        if dk:
            archive_day_keys.add(dk)
    max_id = max(a['id'] for a in archive)

    # 2. Fetch all note articles
    all_notes = fetch_all_note_articles()

    # Build lookup maps for existing archive articles
    # day_key → archive index, normalize_title → archive index
    archive_by_day_key = {}
    archive_by_norm_title = {}
    for i, a in enumerate(archive):
        dk = extract_day_key(a['title'])
        if dk:
            archive_by_day_key[dk] = i
        archive_by_norm_title[normalize_title(a['title'])] = i

    # 3. Process expedition articles: add new, update existing
    new_expeditions = []
    updated_count = 0
    archive_changed = False

    for a in all_notes:
        if not is_expedition(a['title']):
            continue

        nt = normalize_title(a['title'])
        dk = extract_day_key(a['title'])

        # Check if this article already exists in archive
        existing_idx = None
        if nt in archive_by_norm_title:
            existing_idx = archive_by_norm_title[nt]
        elif dk and dk in archive_by_day_key:
            existing_idx = archive_by_day_key[dk]

        if existing_idx is not None:
            # --- UPDATE existing article ---
            existing = archive[existing_idx]
            print(f"  Checking update: No.{existing['num']} {a['title'][:50]}...")
            body_html = fetch_article_body(a['note_key'])
            time.sleep(0.3)

            if not body_html:
                continue

            # Add paid notice if needed
            if a.get('is_paid'):
                body_html += (
                    '\n<p style="text-align:center;margin-top:2rem;padding:1rem;'
                    'background:rgba(201,168,76,0.1);border-radius:8px;'
                    'font-size:0.85rem;color:#8a857e;">'
                    f'この記事の続きは <a href="{a["url"]}" target="_blank" '
                    'rel="noopener" style="color:#c9a84c;">note</a> で'
                    'お読みいただけます（有料記事）</p>'
                )

            plain = re.sub(r'<[^>]+>', '', body_html)
            plain = re.sub(r'\s+', ' ', plain).strip()

            # Only update if body actually changed
            if existing.get('body', '').strip() != body_html.strip():
                existing['body'] = body_html
                existing['excerpt'] = plain[:100]
                existing['title'] = a['title']
                # Update thumbnail
                imgs = re.findall(r'<img[^>]+src="([^"]+)"', body_html)
                existing['thumbnail'] = a.get('eyecatch', '') or (imgs[0] if imgs else existing.get('thumbnail', ''))
                # Update date if was empty
                if not existing.get('date'):
                    date = a['date'].replace('-', '.')
                    existing['date'] = date
                    existing['year'] = date[:4] if date else ''
                updated_count += 1
                archive_changed = True
                print(f"    Updated: No.{existing['num']}")
            else:
                print(f"    No change.")
        else:
            # --- NEW article ---
            new_expeditions.append(a)

    if new_expeditions:
        print(f"\nNew expedition articles to add: {len(new_expeditions)}")
        for a in new_expeditions:
            print(f"  Fetching: {a['title'][:60]}...")
            body_html = fetch_article_body(a['note_key'])
            time.sleep(0.5)

            date = a['date'].replace('-', '.')
            year = date[:4] if date else ''
            country = detect_country(a['title'])

            imgs = re.findall(r'<img[^>]+src="([^"]+)"', body_html)
            thumbnail = a.get('eyecatch', '') or (imgs[0] if imgs else '')

            if a.get('is_paid'):
                body_html += (
                    '\n<p style="text-align:center;margin-top:2rem;padding:1rem;'
                    'background:rgba(201,168,76,0.1);border-radius:8px;'
                    'font-size:0.85rem;color:#8a857e;">'
                    f'この記事の続きは <a href="{a["url"]}" target="_blank" '
                    'rel="noopener" style="color:#c9a84c;">note</a> で'
                    'お読みいただけます（有料記事）</p>'
                )

            plain = re.sub(r'<[^>]+>', '', body_html)
            plain = re.sub(r'\s+', ' ', plain).strip()

            max_id += 1
            archive.append({
                'id': max_id,
                'num': f'{max_id:03d}',
                'title': a['title'],
                'category': detect_expedition_category(a['title']),
                'date': date,
                'year': year,
                'country': country or 'サウジアラビア',
                'excerpt': plain[:100],
                'body': body_html,
                'thumbnail': thumbnail,
            })
            archive_titles.add(normalize_title(a['title']))
            archive_changed = True
            print(f"    Added: No.{max_id:03d} {country or '?'}")

    if archive_changed:
        js = "const articles = " + json.dumps(archive, ensure_ascii=False, indent=2) + ";\n"
        with open(articles_path, 'w') as f:
            f.write(js)
        print(f"\nArchive saved: {len(archive)} articles ({updated_count} updated, {len(new_expeditions)} new)")
    else:
        print(f"\nNo changes to archive. ({updated_count} updated, {len(new_expeditions)} new)")

    # 4. Build note_articles.js (excluding duplicates, expeditions, セブ活動記)
    note_articles = []
    for a in all_notes:
        title = a['title']
        # Skip if in archive
        if normalize_title(title) in archive_titles:
            continue
        # Skip if excluded series
        if is_excluded_from_note(title):
            continue
        # Skip expedition series (already moved to archive)
        if is_expedition(title):
            continue
        # Partial match check
        nt = normalize_title(title)
        is_dup = False
        for at in archive_titles:
            if len(at) > 8 and len(nt) > 8 and (at in nt or nt in at):
                is_dup = True
                break
        if is_dup:
            continue

        date = a['date'].replace('-', '.') if a['date'] else ''
        year = date[:4] if date else ''
        excerpt = re.sub(r'\s+', ' ', (a.get('excerpt') or '')).strip()[:120]

        note_articles.append({
            'title': title,
            'url': a['url'],
            'date': date,
            'year': year,
            'eyecatch': a.get('eyecatch', ''),
            'is_paid': a.get('is_paid', False),
            'excerpt': excerpt,
        })

    # Sort newest first, assign IDs
    note_articles.sort(key=lambda x: x.get('date', ''), reverse=True)
    for i, a in enumerate(note_articles):
        a['id'] = i + 1

    note_js = "const noteArticles = " + json.dumps(note_articles, ensure_ascii=False, indent=2) + ";\n"
    with open(os.path.join(OUT, 'note_articles.js'), 'w') as f:
        f.write(note_js)
    print(f"Note articles: {len(note_articles)}")

    print("\n=== Sync complete ===")

    # 5. Copy output → docs for GitHub Pages deploy
    docs = os.path.join(ROOT, "docs")
    if os.path.isdir(docs):
        import shutil
        for fname in ("articles.js", "note_articles.js"):
            shutil.copy2(os.path.join(OUT, fname), os.path.join(docs, fname))
        print("Copied output → docs/")

    # 6. Git auto-commit & push (best-effort)
    try:
        if not os.path.isdir(os.path.join(ROOT, ".git")):
            print("Git repo not found. Skipping auto-commit.")
            return

        # Check for changes
        status = subprocess.run(
            ["git", "-C", ROOT, "status", "--porcelain"],
            check=False, capture_output=True, text=True
        )
        changed = [line for line in status.stdout.splitlines() if line.strip()]
        if not changed:
            print("No git changes. Skipping commit/push.")
            return

        # Stage updated files
        subprocess.run(["git", "-C", ROOT, "add",
                         "output/articles.js", "output/note_articles.js",
                         "docs/articles.js", "docs/note_articles.js"], check=False)

        # Commit
        msg = time.strftime("Sync note %Y-%m-%d")
        subprocess.run(["git", "-C", ROOT, "commit", "-m", msg], check=False)

        # Push
        subprocess.run(["git", "-C", ROOT, "push", "origin", "main"], check=False)
        print("Git push attempted.")
    except Exception as e:
        print(f"Git auto-commit/push failed: {e}")


if __name__ == '__main__':
    main()
