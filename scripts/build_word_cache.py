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


def _definition_quality_score(defn, meaning_syn, meaning_ant):
    """Heuristic score for how likely a definition is the primary modern
    sense of a word, rather than an archaic/dialectal/narrow one. Kept in
    sync with app._definition_quality_score -- see that docstring for why
    this exists (dictionaryapi.dev doesn't rank senses by commonness)."""
    text = defn.get("definition", "") or ""
    example = defn.get("example", "") or ""
    score = 0
    if len(example) > 20:
        score += 2
    elif example:
        score += 1
    if len(text) >= 30:
        score += 1
    if text.count(";") >= 2 and len(text) < 50:
        score -= 1
    if defn.get("synonyms") or defn.get("antonyms") or meaning_syn or meaning_ant:
        score += 3
    return score


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
    scored_meanings = []
    for m in entry.get("meanings", []):
        m_syn = m.get("synonyms", [])
        m_ant = m.get("antonyms", [])
        defs_sorted = sorted(
            m.get("definitions", []),
            key=lambda d: _definition_quality_score(d, m_syn, m_ant),
            reverse=True,
        )
        if not defs_sorted:
            continue
        top_score = _definition_quality_score(defs_sorted[0], m_syn, m_ant)
        scored_meanings.append((top_score, m.get("partOfSpeech", ""), defs_sorted[:2], m_syn, m_ant))
    scored_meanings.sort(key=lambda x: x[0], reverse=True)

    meanings_out, syn, ant = [], [], []
    for _score, pos, defs_sorted, m_syn, m_ant in scored_meanings[:3]:
        defs = []
        for d in defs_sorted:
            defs.append({"definition": d.get("definition", ""),
                         "example": d.get("example", "")})
            syn += d.get("synonyms", [])
            ant += d.get("antonyms", [])
        syn += m_syn
        ant += m_ant
        if defs:
            meanings_out.append({"partOfSpeech": pos, "definitions": defs})
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


def _atomic_write(path, data):
    # Write-then-rename so a crash/kill mid-write never leaves the live
    # cache file (read by the running Flask app) truncated or corrupt --
    # os.replace is atomic on both POSIX and Windows.
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, path)


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

    old_cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            old_cache = json.load(f)

    # FORCE=1 refetches every word already in `pool` (e.g. to pick up a
    # better definition-ranking heuristic) instead of skipping cached ones.
    # It does NOT start from an empty cache -- `fresh` only holds this run's
    # results, and every checkpoint below writes old_cache merged with
    # fresh, so a crash/interruption mid-run never drops entries that
    # weren't touched yet (or whose refetch failed) below what was already
    # on disk before the run started.
    force = os.environ.get("FORCE") == "1"
    todo = list(pool) if force else [w for w in pool if w not in old_cache]
    fresh = {}

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    print(f"lists={lists}  pool={len(pool)}  cached={len(old_cache)}  to_fetch={len(todo)}")

    ok = fail = 0
    for i, w in enumerate(todo, 1):
        try:
            entry = parse_entry(w, fetch(w))
            if entry:
                fresh[w] = entry
                ok += 1
            else:
                fail += 1
        except Exception:
            fail += 1
        if i % 20 == 0 or i == len(todo):
            merged = {**old_cache, **fresh}
            _atomic_write(CACHE_PATH, merged)
            print(f"  {i}/{len(todo)}  ok={ok} fail={fail} total_cached={len(merged)}")
        time.sleep(0.12)  # be polite to the free API

    merged = {**old_cache, **fresh}
    _atomic_write(CACHE_PATH, merged)
    print(f"DONE  cached={len(merged)}  new_ok={ok}  failed={fail}  -> {CACHE_PATH}")


if __name__ == "__main__":
    main()
