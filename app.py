from flask import Flask, render_template, request, jsonify, Response
from datetime import date, datetime, timedelta
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
    today = date.today()
    # Puzzle number = days since launch date (2026-03-15)
    launch = date(2026, 3, 15)
    puzzle_number = (today - launch).days + 1
    return render_template("index.html",
        title="Daily Word Challenge — WordMaster",
        meta_desc="One word per day. Can you guess today's WordMaster daily challenge in 6 tries?",
        mode="daily", word_length=5, max_guesses=6,
        puzzle_number=puzzle_number,
        today_display=today.strftime("%B %d, %Y"))

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

@app.route("/faq")
def faq():
    return render_template("faq.html",
        title="FAQ — WordMaster",
        meta_desc="Frequently asked questions about WordMaster. Get answers about gameplay, words, stats, privacy and more.")

@app.route("/about")
def about():
    return render_template("about.html",
        title="About WordMaster — Free Word Game",
        meta_desc="WordMaster is a free, browser-based word guessing game. No download needed. Play daily or unlimited!")

@app.route("/contact")
def contact():
    return render_template("contact.html",
        title="Contact Us — WordMaster",
        meta_desc="Get in touch with the WordMaster team. Report bugs, suggest features, or ask anything about the game.")

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

def get_word_for_date(target_date):
    """Return the daily word for a given date object."""
    seed = target_date.year * 10000 + target_date.month * 100 + target_date.day
    random.seed(seed)
    return random.choice(WORDS["daily"]).upper()

@app.route("/archive")
def archive_index():
    """Show the last 30 days of daily words."""
    today = date.today()
    entries = []
    for i in range(30):
        d = today - timedelta(days=i)
        word = get_word_for_date(d)
        entries.append({
            "date": d.strftime("%Y-%m-%d"),
            "date_display": d.strftime("%B %d, %Y"),
            "word": word,
            "is_today": (d == today),
        })
    return render_template("archive.html",
        title="Daily Word Archive — WordMaster",
        meta_desc="Browse past WordMaster daily words. See every daily challenge from the last 30 days.",
        entries=entries,
        today=today.strftime("%Y-%m-%d"))

@app.route("/archive/<date_str>")
def archive_day(date_str):
    """Show the daily word for a specific date."""
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return render_template("404.html", title="Page Not Found — WordMaster"), 404

    today = date.today()
    if target > today:
        return render_template("404.html", title="Page Not Found — WordMaster"), 404

    word = get_word_for_date(target)
    prev_date = (target - timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (target + timedelta(days=1)).strftime("%Y-%m-%d") if target < today else None

    return render_template("archive_day.html",
        title=f"Daily Word {target.strftime('%B %d, %Y')} — WordMaster",
        meta_desc=f"The WordMaster daily word for {target.strftime('%B %d, %Y')}.",
        word=word,
        target_date=target.strftime("%Y-%m-%d"),
        date_display=target.strftime("%B %d, %Y"),
        prev_date=prev_date,
        next_date=next_date,
        is_today=(target == today))

@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html",
        title="Leaderboard & Stats — WordMaster",
        meta_desc="WordMaster global leaderboard. See today's fastest solves and best streaks!")

@app.route("/blog")
def blog():
    posts = [
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

# ─── API ──────────────────────────────────────────────────────

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
    base = "https://wordmaster-game.com"
    urls = [
        "/", "/daily", "/unlimited", "/easy", "/hard",
        "/category/animals", "/category/food",
        "/leaderboard", "/how-to-play", "/faq", "/about", "/contact",
        "/privacy", "/terms", "/blog", "/archive",
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
    txt = "User-agent: *\nAllow: /\nSitemap: https://wordmaster-game.com/sitemap.xml\n"
    return Response(txt, mimetype="text/plain")

@app.route("/ads.txt")
def ads_txt():
    txt = "google.com, pub-3911396624649383, DIRECT, f08c47fec0942fa0\n"
    return Response(txt, mimetype="text/plain")

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", title="Page Not Found — WordMaster"), 404

if __name__ == "__main__":
    app.run(debug=True)
