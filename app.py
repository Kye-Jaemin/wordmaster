from flask import Flask, render_template, request, jsonify, Response
from datetime import date
import json, random, xml.etree.ElementTree as ET, urllib.request, urllib.error

app = Flask(__name__)

with open("words.json", encoding="utf-8") as f:
    WORDS = json.load(f)

def get_daily_word():
    today = date.today()
    seed = today.year * 10000 + today.month * 100 + today.day
    random.seed(seed)
    return random.choice(WORDS["daily"]).upper()

def check_guess(guess, answer):
    guess = guess.upper()
    answer = answer.upper()
    result = []
    answer_chars = list(answer)
    used = [False] * len(answer)

    # First pass: correct position (green)
    for i, ch in enumerate(guess):
        if ch == answer[i]:
            result.append({"letter": ch, "status": "correct"})
            used[i] = True
        else:
            result.append({"letter": ch, "status": "absent"})

    # Second pass: present but wrong position (present)
    for i, ch in enumerate(guess):
        if result[i]["status"] == "correct":
            continue
        for j, ach in enumerate(answer):
            if not used[j] and ch == ach:
                result[i]["status"] = "present"
                used[j] = True
                break

    return result

# ─── Routes ───────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
        title="WordMaster — Free Online Word Guessing Game",
        meta_desc="Play WordMaster, the free daily word guessing game! Guess the 5-letter word in 6 tries. New challenge every day.",
        mode="standard", word_length=5, max_guesses=6)

@app.route("/daily")
def daily():
    return render_template("index.html",
        title="Daily Word Challenge — WordMaster",
        meta_desc="One word per day. Can you guess today's WordMaster daily challenge in 6 tries?",
        mode="daily", word_length=5, max_guesses=6)

@app.route("/unlimited")
def unlimited():
    return render_template("index.html",
        title="Unlimited Word Game — WordMaster",
        meta_desc="Play unlimited rounds of WordMaster! No daily limit — guess as many words as you want.",
        mode="unlimited", word_length=5, max_guesses=6)

@app.route("/easy")
def easy():
    return render_template("index.html",
        title="Easy Mode (4-Letter Words) — WordMaster",
        meta_desc="New to word games? Try WordMaster Easy mode with 4-letter words. Perfect for beginners!",
        mode="easy", word_length=4, max_guesses=6)

@app.route("/hard")
def hard():
    return render_template("index.html",
        title="Hard Mode (6-Letter Words) — WordMaster",
        meta_desc="Up for a challenge? Try WordMaster Hard mode with 6-letter words. Only for word masters!",
        mode="hard", word_length=6, max_guesses=6)

@app.route("/category/<name>")
def category(name):
    cats = {"animals": "Animal Words", "food": "Food Words"}
    cat_label = cats.get(name, name.title())
    return render_template("index.html",
        title=f"{cat_label} Word Game — WordMaster",
        meta_desc=f"Guess {cat_label.lower()} in WordMaster's themed category mode!",
        mode=f"category_{name}", word_length=5, max_guesses=6)

@app.route("/how-to-play")
def how_to_play():
    return render_template("how_to_play.html",
        title="How to Play WordMaster — Rules & Guide",
        meta_desc="Learn how to play WordMaster. Complete rules, tips, and strategies for the word guessing game.")

@app.route("/about")
def about():
    return render_template("about.html",
        title="About WordMaster — Free Word Game",
        meta_desc="WordMaster is a free, browser-based word guessing game. No download needed. Play daily or unlimited!")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html",
        title="Privacy Policy — WordMaster",
        meta_desc="WordMaster privacy policy. Learn how we handle your data.")

@app.route("/terms")
def terms():
    return render_template("terms.html",
        title="Terms of Service — WordMaster",
        meta_desc="WordMaster terms of service and usage conditions.")

@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html",
        title="Leaderboard & Stats — WordMaster",
        meta_desc="WordMaster global leaderboard. See today's fastest solves and best streaks!")

@app.route("/word-of-day")
def word_of_day():
    today = date.today()
    word = get_daily_word()
    # Fetch full dictionary data
    word_data = fetch_full_word_info(word.lower())
    return render_template("word_of_day.html",
        title=f"Word of the Day: {word} — WordMaster",
        meta_desc=f"Today's Word of the Day is {word}. Learn its definition, examples, synonyms, and etymology.",
        word=word,
        word_data=word_data,
        today=today.strftime("%B %d, %Y"))

@app.route("/blog")
def blog():
    posts = [
        {"slug": "top-100-sat-words", "title": "Top 100 SAT Vocabulary Words You Must Know", "date": "2026-04-15", "excerpt": "Boost your SAT score with these high-frequency vocabulary words. Definitions, examples, and memory tips included."},
        {"slug": "ielts-essential-words", "title": "50 Essential IELTS Words to Improve Your Band Score", "date": "2026-04-10", "excerpt": "Master these 50 essential IELTS vocabulary words and watch your writing and speaking scores improve dramatically."},
        {"slug": "wordle-tips", "title": "10 Best Strategies to Win Word Games Every Time", "date": "2026-03-01", "excerpt": "Master word guessing games with these proven starting word strategies and pattern recognition tips."},
        {"slug": "best-starting-words", "title": "The Best Starting Words for Word Games in 2026", "date": "2026-02-20", "excerpt": "CRANE, AUDIO, STARE — we ranked the top 20 starting words for maximum letter coverage."},
        {"slug": "word-game-history", "title": "The History of Word Guessing Games", "date": "2026-02-10", "excerpt": "From newspaper puzzles to viral internet games — how word guessing became a global phenomenon."},
    ]
    return render_template("blog/index.html",
        title="Word Game Blog — Tips, Tricks & Strategies | WordMaster",
        meta_desc="WordMaster blog: expert strategies, best starting words, and word game history.",
        posts=posts)

@app.route("/blog/<slug>")
def blog_post(slug):
    posts = {
        "top-100-sat-words": {
            "title": "Top 100 SAT Vocabulary Words You Must Know",
            "date": "2026-04-15",
            "content": "top_100_sat_words"
        },
        "ielts-essential-words": {
            "title": "50 Essential IELTS Words to Improve Your Band Score",
            "date": "2026-04-10",
            "content": "ielts_essential_words"
        },
        "wordle-tips": {
            "title": "10 Best Strategies to Win Word Games Every Time",
            "date": "2026-03-01",
            "content": "wordle_tips"
        },
        "best-starting-words": {
            "title": "The Best Starting Words for Word Games in 2026",
            "date": "2026-02-20",
            "content": "best_starting_words"
        },
        "word-game-history": {
            "title": "The History of Word Guessing Games",
            "date": "2026-02-10",
            "content": "word_game_history"
        },
    }
    post = posts.get(slug)
    if not post:
        return render_template("404.html"), 404
    return render_template("blog/post.html",
        title=f"{post['title']} — WordMaster Blog",
        meta_desc=f"Read: {post['title']}",
        post=post, slug=slug)

# ─── Helper: Full Dictionary Lookup ──────────────────────────

def fetch_full_word_info(word):
    """Fetch comprehensive word data from Free Dictionary API."""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        req = urllib.request.Request(url, headers={"User-Agent": "WordMaster/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        if not data or not isinstance(data, list):
            return None
        entry = data[0]
        # Phonetic
        phonetic = entry.get("phonetic", "")
        if not phonetic:
            for ph in entry.get("phonetics", []):
                if ph.get("text"):
                    phonetic = ph["text"]
                    break
        # Origin / etymology
        origin = entry.get("origin", "")
        # Meanings: collect up to 3 parts of speech, each with up to 2 defs + examples
        meanings_out = []
        synonyms_all = []
        antonyms_all = []
        for m in entry.get("meanings", [])[:3]:
            pos = m.get("partOfSpeech", "")
            defs_out = []
            for d in m.get("definitions", [])[:2]:
                defs_out.append({
                    "definition": d.get("definition", ""),
                    "example": d.get("example", ""),
                })
                synonyms_all += d.get("synonyms", [])
                antonyms_all += d.get("antonyms", [])
            synonyms_all += m.get("synonyms", [])
            antonyms_all += m.get("antonyms", [])
            if defs_out:
                meanings_out.append({"partOfSpeech": pos, "definitions": defs_out})
        return {
            "word": word.upper(),
            "phonetic": phonetic,
            "origin": origin,
            "meanings": meanings_out,
            "synonyms": list(dict.fromkeys(synonyms_all))[:6],
            "antonyms": list(dict.fromkeys(antonyms_all))[:6],
        }
    except Exception:
        return None

# ─── API ──────────────────────────────────────────────────────

@app.route("/api/word-info")
def api_word_info():
    word = request.args.get("word", "").strip().lower()
    if not word:
        return jsonify({"error": "No word provided"}), 400
    result = fetch_full_word_info(word)
    if result:
        return jsonify(result)
    return jsonify({"word": word.upper(), "meanings": [], "synonyms": [], "antonyms": []}), 200

@app.route("/api/word")
def api_word():
    mode = request.args.get("mode", "standard")
    length = int(request.args.get("length", 5))

    if mode == "daily":
        word = get_daily_word()
    elif mode.startswith("category_"):
        cat = mode.split("_", 1)[1]
        pool = WORDS.get(cat, WORDS["5"])
        word = random.choice(pool).upper()
    else:
        key = str(length)
        pool = WORDS.get(key, WORDS["5"])
        word = random.choice(pool).upper()

    return jsonify({"word": word, "length": len(word)})

@app.route("/api/guess", methods=["POST"])
def api_guess():
    data = request.get_json()
    guess = data.get("guess", "").strip().upper()
    answer = data.get("answer", "").strip().upper()

    if len(guess) != len(answer):
        return jsonify({"error": "Length mismatch"}), 400

    # Validate word exists in any list
    all_words = set()
    for lst in WORDS.values():
        if isinstance(lst, list):
            all_words.update(w.upper() for w in lst)

    if guess not in all_words:
        return jsonify({"error": "Not a valid word", "valid": False}), 200

    result = check_guess(guess, answer)
    won = all(r["status"] == "correct" for r in result)
    return jsonify({"result": result, "valid": True, "won": won})

@app.route("/api/vote", methods=["POST"])
def api_vote():
    # Community difficulty vote — stored in memory (resets on redeploy)
    # For future: persist to a database or file
    return jsonify({"ok": True})

@app.route("/api/hint")
def api_hint():
    word = request.args.get("word", "").strip().lower()
    if not word:
        return jsonify({"error": "No word provided"}), 400

    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        req = urllib.request.Request(url, headers={"User-Agent": "WordMaster/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read())
        if data and isinstance(data, list):
            meanings = data[0].get("meanings", [])
            if meanings:
                m = meanings[0]
                defs = m.get("definitions", [])
                if defs:
                    return jsonify({
                        "word": word.upper(),
                        "partOfSpeech": m.get("partOfSpeech", ""),
                        "definition": defs[0].get("definition", ""),
                        "example": defs[0].get("example", ""),
                    })
    except Exception:
        pass

    # Fallback: letter hint
    return jsonify({
        "word": word.upper(),
        "partOfSpeech": "",
        "definition": f"Starts with '{word[0].upper()}' and ends with '{word[-1].upper()}'",
        "example": "",
    })


# ─── Sitemap & SEO ────────────────────────────────────────────

@app.route("/sitemap.xml")
def sitemap():
    base = "https://wordmaster.store"
    urls = [
        "/", "/daily", "/unlimited", "/easy", "/hard",
        "/category/animals", "/category/food",
        "/leaderboard", "/how-to-play", "/about",
        "/privacy", "/terms", "/blog",
        "/blog/wordle-tips", "/blog/best-starting-words", "/blog/word-game-history"
    ]
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml_lines.append(f"  <url><loc>{base}{u}</loc></url>")
    xml_lines.append("</urlset>")
    return Response("\n".join(xml_lines), mimetype="application/xml")

@app.route("/robots.txt")
def robots():
    txt = "User-agent: *\nAllow: /\nSitemap: https://wordmaster.store/sitemap.xml\n"
    return Response(txt, mimetype="text/plain")

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", title="Page Not Found — WordMaster"), 404

if __name__ == "__main__":
    app.run(debug=True)
