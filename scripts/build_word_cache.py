#!/usr/bin/env python3
"""Build a cached dictionary dataset for the programmatic /word/<word> pages.

Why a build-time cache (not a runtime API call): bot/crawler traffic to
thousands of word pages must not depend on a third-party API per request —
that would be slow, rate-limited, and fragile. We fetch once here and the
Flask route serves from data/word_cache.json with zero runtime API calls.

Usage:
    python scripts/build_word_cache.py                # default seed lists
    python scripts/build_word_cache.py daily high college middle animals food
    python scripts/build_word_cache.py all            # every list in words.json
    LIMIT=120 python scripts/build_word_cache.py daily high   # cap word count

Re-running is incremental: words already in the cache are skipped unless
FORCE=1 is set, so you can grow the dataset over multiple runs.
"""
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS_PATH = os.path.join(ROOT, "words.json")
CACHE_PATH = os.path.join(ROOT, "data", "word_cache.json")

# High-value learning lists first (SAT/GRE/exam vocabulary searchers look for).
DEFAULT_LISTS = ["daily", "high", "college", "middle", "animals", "food"]


def parse_entry(word, data):
    """Shape the Free Dictionary API response like app.fetch_full_word_info."""
    if not data or not isinstance(data, list):
        return None
    entry = data[0]
    phonetic = entry.get("phonetic", "")
    if not phonetic:
        for ph in entry.get("phonetics", []):
            if ph.get("text"):
                phonetic = ph["text"]
                break
    meanings_out, syn, ant = [], [], []
    for m in entry.get("meanings", [])[:3]:
        defs = []
        for d in m.get("definitions", [])[:2]:
            defs.append({"definition": d.get("definition", ""),
                         "example": d.get("example", "")})
            syn += d.get("synonyms", [])
            ant += d.get("antonyms", [])
        syn += m.get("synonyms", [])
        ant += m.get("antonyms", [])
        if defs:
            meanings_out.append({"partOfSpeech": m.get("partOfSpeech", ""),
                                 "definitions": defs})
    if not meanings_out:
        return None  # no usable definition -> don't cache (avoids thin pages)
    return {
        "word": word.lower(),
        "phonetic": phonetic,
        "origin": entry.get("origin", ""),
        "meanings": meanings_out,
        "synonyms": list(dict.fromkeys(syn))[:6],
        "antonyms": list(dict.fromkeys(ant))[:6],
    }


def fetch(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    req = urllib.request.Request(url, headers={"User-Agent": "WordMaster-cache/1.0"})
    with urllib.request.urlopen(req, timeout=4) as resp:
        return json.loads(resp.read())


def main():
    with open(WORDS_PATH, encoding="utf-8") as f:
        words = json.load(f)

    args = [a for a in sys.argv[1:] if a]
    if args == ["all"]:
        lists = [k for k, v in words.items() if isinstance(v, list)]
    else:
        lists = args or DEFAULT_LISTS

    pool = []
    for key in lists:
        for w in words.get(key, []):
            wl = w.lower()
            if wl.isalpha() and wl not in pool:
                pool.append(wl)

    limit = int(os.environ.get("LIMIT", "0"))
    if limit:
        pool = pool[:limit]

    cache = {}
    if os.path.exists(CACHE_PATH) and os.environ.get("FORCE") != "1":
        with open(CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    todo = [w for w in pool if w not in cache]
    print(f"lists={lists}  pool={len(pool)}  cached={len(cache)}  to_fetch={len(todo)}")

    ok = fail = 0
    for i, w in enumerate(todo, 1):
        try:
            entry = parse_entry(w, fetch(w))
            if entry:
                cache[w] = entry
                ok += 1
            else:
                fail += 1
        except Exception:
            fail += 1
        if i % 20 == 0 or i == len(todo):
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=0, sort_keys=True)
            print(f"  {i}/{len(todo)}  ok={ok} fail={fail} total_cached={len(cache)}")
        time.sleep(0.12)  # be polite to the free API

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=0, sort_keys=True)
    print(f"DONE  cached={len(cache)}  new_ok={ok}  failed={fail}  -> {CACHE_PATH}")


if __name__ == "__main__":
    main()
