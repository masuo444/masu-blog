#!/usr/bin/env python3
"""Translate articles.js entries from Japanese to English using DeepL API."""

import os
import re
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import ssl

try:
    import certifi  # type: ignore
except Exception:
    certifi = None

ARTICLES_PATH = os.path.join(os.path.dirname(__file__), "output", "articles.js")

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


def load_articles(path):
    """Load articles from articles.js file."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    json_str = content.replace('const articles = ', '', 1).rstrip(';\n')
    return json.loads(json_str)


def save_articles(path, articles):
    """Save articles back to articles.js file."""
    js_content = "const articles = " + json.dumps(articles, ensure_ascii=False, indent=2) + ";\n"
    with open(path, 'w', encoding='utf-8') as f:
        f.write(js_content)


def deepl_translate(text, api_key, tag_handling=None):
    """Translate text using DeepL API."""
    if not text or not text.strip():
        return ''

    # Determine API endpoint (free vs pro)
    if api_key.endswith(':fx'):
        url = 'https://api-free.deepl.com/v2/translate'
    else:
        url = 'https://api.deepl.com/v2/translate'

    params = {
        'text': text,
        'source_lang': 'JA',
        'target_lang': 'EN',
    }
    if tag_handling:
        params['tag_handling'] = tag_handling

    data = urllib.parse.urlencode(params).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Authorization': f'DeepL-Auth-Key {api_key}',
        'Content-Type': 'application/x-www-form-urlencoded',
    })

    def _load_response(resp):
        result = json.loads(resp.read().decode('utf-8'))
        return result['translations'][0]['text']

    def _build_ssl_context():
        if certifi is not None:
            return ssl.create_default_context(cafile=certifi.where())
        return ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, context=_build_ssl_context()) as resp:
            return _load_response(resp)
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            # Fallback: allow unverified SSL context if local trust store is missing.
            with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as resp:
                return _load_response(resp)
        raise
    except ssl.SSLCertVerificationError:
        with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as resp:
            return _load_response(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"  DeepL API error {e.code}: {body}")
        raise


def translate_article(article, api_key):
    """Translate a single article's fields."""
    # title (plain text)
    title_en = deepl_translate(article['title'], api_key)
    time.sleep(0.3)

    # excerpt (plain text)
    excerpt_en = deepl_translate(article['excerpt'], api_key)
    time.sleep(0.3)

    # body (HTML — preserve tags)
    body_en = deepl_translate(article['body'], api_key, tag_handling='html')
    time.sleep(0.5)

    # country
    country_en = COUNTRY_EN.get(article.get('country', ''), article.get('country', ''))

    return {
        'title_en': title_en,
        'excerpt_en': excerpt_en,
        'body_en': body_en,
        'country_en': country_en,
    }


def main():
    parser = argparse.ArgumentParser(description='Translate articles.js to English via DeepL')
    parser.add_argument('--force', action='store_true', help='Re-translate all articles (ignore existing)')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of articles to translate (0=all)')
    args = parser.parse_args()

    api_key = os.environ.get('DEEPL_API_KEY', '')
    if not api_key:
        print("ERROR: Set DEEPL_API_KEY environment variable")
        print("  export DEEPL_API_KEY='your-deepl-api-key'")
        return

    print(f"Loading {ARTICLES_PATH} ...")
    articles = load_articles(ARTICLES_PATH)
    print(f"  {len(articles)} articles loaded")

    translated = 0
    skipped = 0
    errors = 0

    for i, article in enumerate(articles):
        # Add country_en if missing (no API needed)
        if 'country_en' not in article:
            article['country_en'] = COUNTRY_EN.get(article.get('country', ''), article.get('country', ''))

        # Skip if already translated (unless --force)
        if not args.force and article.get('title_en'):
            skipped += 1
            continue

        if args.limit and translated >= args.limit:
            print(f"  Reached limit of {args.limit} articles")
            break

        print(f"  [{i+1}/{len(articles)}] Translating: {article['title'][:40]}...")
        try:
            en_fields = translate_article(article, api_key)
            article.update(en_fields)
            translated += 1

            # Save after each article (incremental)
            if translated % 5 == 0:
                save_articles(ARTICLES_PATH, articles)
                print(f"    (saved checkpoint at {translated} articles)")
        except Exception as e:
            print(f"  ERROR translating article {article['id']}: {e}")
            errors += 1
            # Save progress before potentially stopping
            save_articles(ARTICLES_PATH, articles)
            time.sleep(2)

    # Final save
    save_articles(ARTICLES_PATH, articles)
    print(f"\nDone! Translated: {translated}, Skipped: {skipped}, Errors: {errors}")


if __name__ == '__main__':
    main()
