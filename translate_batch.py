#!/usr/bin/env python3
"""Helper to extract/merge translation batches for articles.js"""

import os
import json
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ARTICLES_PATH = os.path.join(ROOT, "output", "articles.js")
BATCH_DIR = os.path.join(ROOT, "translation_batches")

COUNTRY_EN = {
    'フィリピン': 'Philippines', 'アイルランド': 'Ireland',
    'マレーシア': 'Malaysia', 'アメリカ': 'USA',
    'ドバイ(UAE)': 'Dubai (UAE)', 'スペイン': 'Spain',
    'フランス': 'France', 'ラトビア': 'Latvia',
    'リトアニア': 'Lithuania', 'マルタ': 'Malta',
    'ポルトガル': 'Portugal', 'ノルウェー': 'Norway',
    'デンマーク': 'Denmark', 'ポーランド': 'Poland',
    'スウェーデン': 'Sweden', 'イギリス': 'UK',
    'ギリシャ': 'Greece', 'キプロス': 'Cyprus',
    '日本': 'Japan', '中国': 'China',
    'ルーマニア': 'Romania', 'ベルギー': 'Belgium',
    'バーレーン': 'Bahrain', 'サウジアラビア': 'Saudi Arabia',
    '台湾': 'Taiwan',
}


def load_articles():
    with open(ARTICLES_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    json_str = content.replace('const articles = ', '', 1).rstrip(';\n')
    return json.loads(json_str)


def save_articles(articles):
    js = "const articles = " + json.dumps(articles, ensure_ascii=False, indent=2) + ";\n"
    with open(ARTICLES_PATH, 'w', encoding='utf-8') as f:
        f.write(js)


def extract_batches(batch_size=20):
    """Extract untranslated articles into batch files."""
    os.makedirs(BATCH_DIR, exist_ok=True)
    articles = load_articles()
    untranslated = [a for a in articles if not a.get('title_en')]
    print(f"Total untranslated: {len(untranslated)}")

    batch_num = 0
    for i in range(0, len(untranslated), batch_size):
        batch = untranslated[i:i+batch_size]
        batch_data = []
        for a in batch:
            batch_data.append({
                'id': a['id'],
                'title': a['title'],
                'excerpt': a['excerpt'],
                'body': a['body'],
                'country': a.get('country', ''),
            })
        batch_num += 1
        path = os.path.join(BATCH_DIR, f"batch_{batch_num:03d}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(batch_data, f, ensure_ascii=False, indent=2)
        print(f"  batch_{batch_num:03d}.json: {len(batch)} articles (IDs {batch[0]['id']}-{batch[-1]['id']})")

    print(f"\nCreated {batch_num} batch files in {BATCH_DIR}")


def merge_translations():
    """Merge translated batch files back into articles.js."""
    articles = load_articles()
    article_map = {a['id']: a for a in articles}

    merged_count = 0
    batch_files = sorted(f for f in os.listdir(BATCH_DIR) if f.startswith('translated_'))

    for bf in batch_files:
        path = os.path.join(BATCH_DIR, bf)
        with open(path, 'r', encoding='utf-8') as f:
            translated = json.load(f)
        for t in translated:
            aid = t['id']
            if aid in article_map:
                if t.get('title_en'):
                    article_map[aid]['title_en'] = t['title_en']
                if t.get('excerpt_en'):
                    article_map[aid]['excerpt_en'] = t['excerpt_en']
                if t.get('body_en'):
                    article_map[aid]['body_en'] = t['body_en']
                article_map[aid]['country_en'] = COUNTRY_EN.get(
                    article_map[aid].get('country', ''),
                    article_map[aid].get('country', '')
                )
                merged_count += 1

    save_articles(articles)
    print(f"Merged {merged_count} translations into articles.js")


def status():
    """Show translation status."""
    articles = load_articles()
    total = len(articles)
    done = sum(1 for a in articles if a.get('title_en'))
    print(f"Translated: {done}/{total} ({done*100//total}%)")
    cats = {}
    for a in articles:
        c = a['category']
        if c not in cats:
            cats[c] = {'total': 0, 'done': 0}
        cats[c]['total'] += 1
        if a.get('title_en'):
            cats[c]['done'] += 1
    for k, v in cats.items():
        pct = v['done'] * 100 // v['total'] if v['total'] else 0
        bar = '█' * (pct // 5) + '░' * (20 - pct // 5)
        print(f"  {k:12s} {bar} {v['done']:3d}/{v['total']:3d} ({pct}%)")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'extract':
        size = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        extract_batches(size)
    elif cmd == 'merge':
        merge_translations()
    elif cmd == 'status':
        status()
    else:
        print(f"Usage: {sys.argv[0]} [extract|merge|status]")
