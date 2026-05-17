from flask import Flask, render_template, request, jsonify, Response, redirect, session
from datetime import date, timedelta
import json, random, re, xml.etree.ElementTree as ET, urllib.request, urllib.error

# ── News Cache (refreshed once per day) ───────────────────────
_news_cache = {"date": None, "articles": [], "word": None}

def fetch_news_articles():
    """Fetch BBC World News RSS and return list of article dicts (cached daily)."""
    global _news_cache
    today_str = str(date.today())
    if _news_cache["date"] == today_str and _news_cache["articles"]:
        return _news_cache["articles"]
    try:
        url = "https://feeds.bbci.co.uk/news/world/rss.xml"
        req = urllib.request.Request(url, headers={"User-Agent": "WordMaster/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        articles = []
        for item in root.findall(".//item")[:6]:
            title = item.findtext("title", "").strip()
            desc  = item.findtext("description", "").strip()
            link  = item.findtext("link", "").strip()
            pub   = item.findtext("pubDate", "").strip()
            # Use full description (was [:180]) so word picker has more body text to draw from
            desc  = re.sub(r"<[^>]+>", "", desc).strip()
            if title and link:
                articles.append({"title": title, "description": desc,
                                  "link": link, "source": "BBC News", "pubDate": pub})
        _news_cache = {"date": today_str, "articles": articles, "word": None}
        return articles
    except Exception:
        return []

def pick_news_word(articles):
    """Pick a valid 5-letter game word from today's news headlines (cached daily)."""
    global _news_cache
    today_str = str(date.today())
    if _news_cache["date"] == today_str and _news_cache.get("word"):
        return _news_cache["word"], _news_cache.get("word_source", "")
    # Build combined valid word set from all word lists
    all_valid = set()
    for lst in WORDS.values():
        if isinstance(lst, list):
            all_valid.update(w.upper() for w in lst)
    # Extract 5-letter alpha words from headlines + descriptions
    candidates = []
    for art in articles:
        for w in re.findall(r"\b[a-zA-Z]{5}\b", art["title"] + " " + art["description"]):
            wu = w.upper()
            if wu in all_valid:
                candidates.append((wu, art["title"]))
    if candidates:
        seed = date.today().year * 10000 + date.today().month * 100 + date.today().day + 999
        random.seed(seed)
        word, source = random.choice(candidates)
    else:
        word, source = get_daily_word(), ""
    _news_cache["word"] = word
    _news_cache["word_source"] = source
    return word, source

app = Flask(__name__)
app.secret_key = "wordmaster-lang-2024-xK9#mQ"

with open("words.json", encoding="utf-8") as f:
    WORDS = json.load(f)

# ─── Language Support ──────────────────────────────────────────

@app.context_processor
def inject_lang():
    """Inject current language into every template automatically."""
    return dict(lang=session.get("lang", "en"))

@app.route("/set-lang/<lang>")
def set_lang(lang):
    """Set the display language and redirect back."""
    if lang in ("en", "ko"):
        session["lang"] = lang
    return redirect(request.referrer or "/")

def get_daily_word():
    today = date.today()
    seed = today.year * 10000 + today.month * 100 + today.day
    random.seed(seed)
    return random.choice(WORDS["daily"]).upper()

def get_word_for_date(d):
    """Get the daily word for any specific date."""
    seed = d.year * 10000 + d.month * 100 + d.day
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
        title="WordMaster — Free Word Guessing Game | Daily & Unlimited",
        meta_desc="Play WordMaster free online word guessing game. Guess the hidden 5-letter word in 6 tries. Daily challenge, unlimited mode, news word puzzle and more. No signup needed.",
        mode="standard", word_length=5, max_guesses=6)

@app.route("/daily")
def daily():
    return render_template("index.html",
        title="Daily Word Challenge — WordMaster | Free Word Puzzle",
        meta_desc="Play today's WordMaster daily word challenge. One new 5-letter word every day, shared by all players. Guess in 6 tries and track your streak. Free, no account needed.",
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
        title="About WordMaster — Daily Word Game That Builds Vocabulary",
        meta_desc="WordMaster is a daily word puzzle that tracks the vocabulary you learn. A one-person project built to make word games actually teach. Play, learn, remember.")

@app.route("/contact")
def contact():
    return render_template("contact.html",
        title="Contact WordMaster — Get in Touch",
        meta_desc="Contact the WordMaster team. Report bugs, suggest words, or ask questions about the free word guessing game.")

@app.route("/faq")
def faq():
    return render_template("faq.html",
        title="FAQ — WordMaster | Frequently Asked Questions",
        meta_desc="Answers to the most common questions about WordMaster. How the game works, word lists, scores, streaks, and more.")

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
    # Word of Day was a static dictionary page that duplicated content already
    # surfaced in the Daily Challenge result panel. Redirect permanently so
    # any existing inbound links still land somewhere useful.
    return redirect("/daily", code=301)

@app.route("/archive")
def archive():
    today = date.today()
    entries = []
    for i in range(30):
        d = today - timedelta(days=i)
        entries.append({
            "date":         d.strftime("%Y-%m-%d"),
            "date_display": d.strftime("%B %d, %Y"),
            "word":         get_word_for_date(d),
            "is_today":     i == 0,
        })
    return render_template("archive.html",
        title="Daily Word Archive — WordMaster | Replay Past Puzzles",
        meta_desc="Browse and replay the past 30 days of WordMaster daily word challenges. Click any date to see the word, its definition, etymology, and synonyms. Free vocabulary practice.",
        entries=entries)

@app.route("/archive/<date_str>")
def archive_day(date_str):
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        return redirect("/archive")
    today  = date.today()
    if d > today:
        return redirect("/archive")
    word      = get_word_for_date(d)
    is_today  = d == today
    prev_d    = d - timedelta(days=1)
    next_d    = d + timedelta(days=1)
    prev_date = prev_d.strftime("%Y-%m-%d") if (today - prev_d).days <= 29 else None
    next_date = next_d.strftime("%Y-%m-%d") if next_d <= today else None
    return render_template("archive_day.html",
        title=f"WordMaster Archive: {d.strftime('%B %d, %Y')}",
        meta_desc=f"See the WordMaster daily word for {d.strftime('%B %d, %Y')} and its definition.",
        word=word,
        date_display=d.strftime("%B %d, %Y"),
        is_today=is_today,
        prev_date=prev_date,
        next_date=next_date)

@app.route("/middle")
def middle_level():
    return render_template("index.html",
        title="Middle School Word Game — WordMaster",
        meta_desc="Daily 5-letter word puzzle using middle school vocabulary. Build core English fluency through play. Free, no signup needed.",
        mode="category_middle", word_length=5, max_guesses=6)

@app.route("/high")
def high_level():
    return render_template("index.html",
        title="High School Word Game — WordMaster",
        meta_desc="5-letter word puzzle using high school and SAT-prep vocabulary. Strengthen academic English daily. Free, no signup.",
        mode="category_high", word_length=5, max_guesses=6)

@app.route("/college")
def college_level():
    return render_template("index.html",
        title="College Word Game — WordMaster",
        meta_desc="Advanced 5-letter word puzzle using college and GRE-level vocabulary. Sharpen academic English while you play. Free.",
        mode="category_college", word_length=5, max_guesses=6)

@app.route("/custom")
def custom_words():
    return render_template("custom_words.html",
        title="My Custom Words — WordMaster",
        meta_desc="Build your own word list and practice with it. Add personal vocabulary you want to master and play through them with WordMaster.")

# ─── Blog tag map ─────────────────────────────────────────────
# Marks each blog post with the puzzle format it is primarily about, so the
# blog index and post pages can display a coloured badge ("Tile Guess",
# "Anagram", "Hangman", or "Vocab Learning" for game-agnostic vocabulary posts).
BLOG_TAGS = {
    # Tile Guess specific (color-tile strategy, 5-letter starting words)
    "word-game-tips":               "tile",
    "best-starting-words":          "tile",
    "common-5-letter-words":        "tile",
    "pattern-recognition-word-games": "tile",
    # Anagram specific
    "anagram-strategy":             "anagram",
    # Hangman specific
    "hangman-letter-frequency":     "hangman",
    # General overview / multi-format
    "three-puzzle-formats":         "vocab",
    "word-game-history":            "vocab",
    # Vocabulary learning (game-agnostic)
    "top-100-sat-words":            "vocab",
    "ielts-essential-words":        "vocab",
    "daily-habits-vocabulary":      "vocab",
    "science-of-word-games":        "vocab",
    "word-roots-prefixes-suffixes": "vocab",
    "vocabulary-habit-building":    "vocab",
    "reading-comprehension-word-games": "vocab",
    "greek-latin-roots-english":    "vocab",
    "business-english-vocabulary":  "vocab",
    "word-games-children-reading":  "vocab",
}

# ─── Alternate puzzle formats: Anagram & Hangman ──────────────
# Same vocabulary sources as the Tile Guess game, presented as different puzzle mechanics.
_CATEGORY_TO_MODE = {
    "middle":  ("category_middle",  "Middle School",     5),
    "high":    ("category_high",    "High School",       5),
    "college": ("category_college", "College",           5),
    "animals": ("category_animals", "Animals",           5),
    "food":    ("category_food",    "Food",              5),
    "daily":   ("daily",            "Daily",             5),
    "custom":  ("custom",           "Custom Words",      5),
    "news":    ("news",             "News Words",        5),
    "easy":    ("easy",             "Easy (4 Letters)",  4),
    "hard":    ("hard",             "Hard (6 Letters)",  6),
}
_TILE_URL_FOR_CATEGORY = {
    None:      "/",
    "middle":  "/middle",
    "high":    "/high",
    "college": "/college",
    "animals": "/category/animals",
    "food":    "/category/food",
    "daily":   "/daily",
    "custom":  "/custom",
    "news":    "/news-challenge",
    "easy":    "/easy",
    "hard":    "/hard",
}

def _selector_urls(prefix):
    """Build the category + difficulty URLs for a given puzzle format prefix.

    prefix = "" for Tile Guess (the homepage / standard 5-letter game)
    prefix = "/anagram" or "/hangman" for the alternate puzzle formats
    """
    if prefix == "":
        # Tile Guess uses bespoke URLs from the original site structure
        return {
            "middle":  "/middle",
            "high":    "/high",
            "college": "/college",
            "custom":  "/custom",
            "news":    "/news-challenge",
            "animals": "/category/animals",
            "food":    "/category/food",
            "easy":    "/easy",
            "normal":  "/",
            "hard":    "/hard",
        }
    return {
        "middle":  f"{prefix}/middle",
        "high":    f"{prefix}/high",
        "college": f"{prefix}/college",
        "custom":  f"{prefix}/custom",
        "news":    f"{prefix}/news",
        "animals": f"{prefix}/animals",
        "food":    f"{prefix}/food",
        "easy":    f"{prefix}/easy",
        "normal":  prefix,
        "hard":    f"{prefix}/hard",
    }

@app.context_processor
def inject_selector_urls():
    """Inject puzzle-format-aware vocab + difficulty switcher URLs into every template,
    plus the current_format key used by the three Game Format cards to mark which one
    the user is currently playing.
    """
    path = request.path or "/"
    if path.startswith("/anagram"):
        prefix = "/anagram"
        current_format = "anagram"
    elif path.startswith("/hangman"):
        prefix = "/hangman"
        current_format = "hangman"
    else:
        prefix = ""
        current_format = "tile"
    return {
        "puzzle_prefix":  prefix,
        "selector_urls":  _selector_urls(prefix),
        "current_format": current_format,
    }

def _puzzle_context(category):
    """Build mode, label, word_length, and sibling URLs for an alternate-format puzzle page."""
    mode, label, length = _CATEGORY_TO_MODE.get(category, ("standard", "Standard 5-Letter", 5))
    cat_suffix = f"/{category}" if category in _CATEGORY_TO_MODE else ""
    return {
        "mode": mode,
        "category_label": label,
        "word_length": length,
        # Template variable retains the old name for backward compatibility,
        # but it now points to the Tile Guess URL for the matching category.
        "wordle_url":  _TILE_URL_FOR_CATEGORY.get(category, "/"),
        "anagram_url": f"/anagram{cat_suffix}",
        "hangman_url": f"/hangman{cat_suffix}",
    }

@app.route("/anagram")
@app.route("/anagram/<category>")
def anagram(category=None):
    ctx = _puzzle_context(category)
    return render_template("anagram_game.html",
        title=f"Anagram Word Puzzle — {ctx['category_label']} | WordMaster",
        meta_desc="Anagram word puzzle: unscramble the letters to form a word. Reinforces spelling and letter-level vocabulary recall. Free, no signup.",
        **ctx)

@app.route("/hangman")
@app.route("/hangman/<category>")
def hangman(category=None):
    ctx = _puzzle_context(category)
    return render_template("hangman_game.html",
        title=f"Hangman Word Puzzle — {ctx['category_label']} | WordMaster",
        meta_desc="Hangman word game: guess letters before lives run out. Classic spelling and letter-frequency practice with curated vocabulary. Free.",
        **ctx)

@app.route("/my-words")
def my_words():
    return render_template("my_words.html",
        title="My Words — Your WordMaster Vocabulary Log",
        meta_desc="Every word you've encountered in WordMaster, tracked with dates and stats. Your personal vocabulary log, stored locally on your device.")

@app.route("/my-weak-words")
def my_weak_words():
    return render_template("my_weak_words.html",
        title="Weak Words — Targeted Practice | WordMaster",
        meta_desc="Words you couldn't solve, kept here for focused practice. Master them in any WordMaster game mode and they'll graduate off the list.")

@app.route("/my-progress")
def my_progress():
    return render_template("my_progress.html",
        title="My Progress — Vocabulary Growth Dashboard | WordMaster",
        meta_desc="Track your vocabulary growth, daily streak, and game activity over time. Personal learning dashboard with charts, stored locally.")

@app.route("/blog")
def blog():
    posts = [
        {"slug": "anagram-strategy", "title": "Anagram Strategy: Where I Lose Words I Thought I Knew", "title_ko": "애너그램 전략: 내가 안다고 생각한 단어를 놓치는 지점", "date": "2026-05-17", "excerpt": "Anagram is not the easy warm-up I thought it was. Here is what I started doing differently after losing more anagrams than I expected.", "excerpt_ko": "애너그램은 제가 생각했던 쉬운 워밍업이 아니었습니다. 예상보다 더 많은 애너그램을 놓치고 난 뒤 무엇을 다르게 하기 시작했는지."},
        {"slug": "hangman-letter-frequency", "title": "Hangman as Letter-Frequency Practice", "title_ko": "행맨, 글자 빈도 직관을 키우는 도구", "date": "2026-05-17", "excerpt": "Hangman taught me what English actually looks like. The instinct for which letters carry information transfers to every other word puzzle.", "excerpt_ko": "행맨은 영어가 실제로 어떻게 생겼는지 가르쳐 줍니다. 어떤 글자가 정보를 담는지에 대한 직관은 모든 단어 퍼즐에 그대로 이전됩니다."},
        {"slug": "three-puzzle-formats", "title": "Three Puzzle Formats for the Same Word: Tile Guess, Anagram, Hangman", "title_ko": "한 단어, 세 가지 퍼즐: 타일 게임, 애너그램, 행맨", "date": "2026-05-16", "excerpt": "Three puzzle mechanics train three different vocabulary skills — recognition, production, and letter-level intuition. Here is how I use each.", "excerpt_ko": "세 가지 퍼즐 메카닉이 어휘의 세 가지 다른 능력을 훈련합니다 — 인지, 생산, 글자 단위 직관. 각각을 어떻게 활용하는지."},
        {"slug": "daily-habits-vocabulary", "title": "5 Daily Habits That Will Rapidly Expand Your Vocabulary", "date": "2026-04-25", "excerpt": "Small daily actions compound into big vocabulary gains. Here are five research-backed habits you can start today."},
        {"slug": "science-of-word-games", "title": "The Science Behind Word Games: How Puzzles Boost Your Brain", "date": "2026-04-22", "excerpt": "Research shows that daily word puzzles improve memory, focus, and problem-solving. Here's what the science actually says."},
        {"slug": "common-5-letter-words", "title": "The 50 Most Common 5-Letter Words in English (And How to Use Them)", "date": "2026-05-03", "excerpt": "These 50 high-frequency 5-letter words appear constantly in word games and everyday English. Master them to gain a serious advantage."},
        {"slug": "word-roots-prefixes-suffixes", "title": "Word Roots, Prefixes and Suffixes: The Ultimate Vocabulary Cheat Sheet", "date": "2026-04-30", "excerpt": "Learn 30 Latin and Greek roots that unlock thousands of English words. One root can teach you 20 new words at once."},
        {"slug": "vocabulary-habit-building", "title": "How to Build a Vocabulary Habit That Actually Sticks", "date": "2026-04-27", "excerpt": "Most vocabulary-building attempts fail within a week. Here is the habit-building science that makes the difference."},
        {"slug": "top-100-sat-words", "title": "Top 100 SAT Vocabulary Words You Must Know", "title_ko": "SAT 필수 어휘 100개", "date": "2026-04-15", "excerpt": "Boost your SAT score with these high-frequency vocabulary words. Definitions, examples, and memory tips included.", "excerpt_ko": "고빈출 SAT 어휘로 점수를 올리세요. 정의, 예문, 암기 팁이 포함되어 있습니다."},
        {"slug": "ielts-essential-words", "title": "50 Essential IELTS Words to Improve Your Band Score", "date": "2026-04-10", "excerpt": "Master these 50 essential IELTS vocabulary words and watch your writing and speaking scores improve dramatically."},
        {"slug": "reading-comprehension-word-games", "title": "How Word Games Improve Reading Comprehension", "date": "2026-04-03", "excerpt": "The link between word game performance and reading ability is stronger than most people realize. Here is what research shows."},
        {"slug": "greek-latin-roots-english", "title": "Greek and Latin Roots Every English Learner Should Know", "date": "2026-03-28", "excerpt": "Unlock the building blocks of English. These 25 classical roots appear in thousands of modern words across every subject."},
        {"slug": "pattern-recognition-word-games", "title": "Pattern Recognition: The Hidden Skill That Wins Word Puzzles", "date": "2026-03-20", "excerpt": "The best word puzzle players think differently. Here is how to train your pattern recognition to solve puzzles faster."},
        {"slug": "word-game-tips", "title": "10 Best Strategies to Win Word Games Every Time", "title_ko": "단어 게임 승리 전략 10가지", "date": "2026-03-01", "excerpt": "Master word guessing games with these proven starting word strategies and pattern recognition tips.", "excerpt_ko": "검증된 시작 단어 전략과 패턴 인지 팁으로 단어 추측 게임을 마스터하세요."},
        {"slug": "best-starting-words", "title": "The Best Starting Words for Word Games in 2026", "title_ko": "2026년 단어 게임 최고의 시작 단어", "date": "2026-02-20", "excerpt": "CRANE, AUDIO, STARE — we ranked the top 20 starting words for maximum letter coverage.", "excerpt_ko": "CRANE, AUDIO, STARE — 글자 커버리지를 최대화하는 시작 단어 20개를 순위 매겼습니다."},
        {"slug": "business-english-vocabulary", "title": "40 Essential Business English Words You Need at Work", "date": "2026-02-15", "excerpt": "From boardroom to email, these 40 business vocabulary words will make you sound more confident and professional."},
        {"slug": "word-games-children-reading", "title": "How Word Games Help Children Learn to Read", "date": "2026-02-12", "excerpt": "Word puzzles are not just for adults. Research shows they significantly accelerate phonics, spelling, and reading fluency in children."},
        {"slug": "word-game-history", "title": "The History of Word Guessing Games", "date": "2026-02-10", "excerpt": "From newspaper puzzles to viral internet games — how word guessing became a global phenomenon."},
    ]
    # Attach a tag to each post so the index can show a colour-coded badge
    for p in posts:
        p["tag"] = BLOG_TAGS.get(p["slug"], "vocab")
    lang = session.get("lang", "en")
    page_title = ("워드마스터 블로그 — 어휘 팁과 단어 게임 가이드 | WordMaster"
                  if lang == "ko"
                  else "Word Game Blog — Vocabulary Tips, Brain Science & Strategies | WordMaster")
    page_meta  = ("WordMaster 블로그: 어휘 강화 전략, 단어 게임의 두뇌 과학, SAT/IELTS 단어 리스트, 그리고 모든 퍼즐을 이기는 검증된 전술."
                  if lang == "ko"
                  else "WordMaster blog: expert vocabulary-building strategies, brain science behind word games, SAT/IELTS word lists, and proven tactics to win every puzzle.")
    return render_template("blog/index.html",
        title=page_title,
        meta_desc=page_meta,
        posts=posts)

@app.route("/blog/<slug>")
def blog_post(slug):
    posts = {
        "anagram-strategy": {
            "title": "Anagram Strategy: Where I Lose Words I Thought I Knew",
            "title_ko": "애너그램 전략: 내가 안다고 생각한 단어를 놓치는 지점",
            "date": "2026-05-17",
            "content": "anagram_strategy",
            "meta_desc": "Anagram is not the easy warm-up most players think. A first-person look at why anagram exposes the gap between recognizing a word and owning it — and how to close that gap.",
            "meta_desc_ko": "애너그램은 대부분의 사람들이 생각하는 쉬운 워밍업이 아닙니다. 단어를 인지하는 것과 진짜로 소유하는 것 사이의 격차를 애너그램이 어떻게 드러내는지, 그리고 그 격차를 어떻게 줄이는지에 대한 1인칭 기록.",
            "related": ["three-puzzle-formats", "hangman-letter-frequency", "word-roots-prefixes-suffixes"]
        },
        "hangman-letter-frequency": {
            "title": "Hangman as Letter-Frequency Practice",
            "title_ko": "행맨, 글자 빈도 직관을 키우는 도구",
            "date": "2026-05-17",
            "content": "hangman_letter_frequency",
            "meta_desc": "Hangman is the only word puzzle that teaches what English actually looks like. How letter-frequency intuition built in hangman transfers to every other word puzzle and to reading.",
            "meta_desc_ko": "행맨은 영어가 실제로 어떻게 생겼는지 가르쳐 주는 유일한 단어 퍼즐입니다. 행맨에서 쌓은 글자 빈도 직관이 다른 모든 단어 퍼즐과 읽기로 어떻게 이전되는지.",
            "related": ["three-puzzle-formats", "anagram-strategy", "pattern-recognition-word-games"]
        },
        "three-puzzle-formats": {
            "title": "Three Puzzle Formats for the Same Word: Tile Guess, Anagram, Hangman",
            "title_ko": "한 단어, 세 가지 퍼즐: 타일 게임, 애너그램, 행맨",
            "date": "2026-05-16",
            "content": "three_puzzle_formats",
            "meta_desc": "Tile Guess, Anagram, and Hangman train three different vocabulary skills. Why WordMaster offers all three side-by-side, and which one to play when.",
            "meta_desc_ko": "타일 게임, 애너그램, 행맨이 어휘의 세 가지 다른 능력을 훈련합니다. WordMaster가 세 가지를 함께 제공하는 이유와 언제 무엇을 플레이해야 하는지.",
            "related": ["word-game-tips", "best-starting-words", "pattern-recognition-word-games"]
        },
        "top-100-sat-words": {
            "title": "Top 100 SAT Vocabulary Words You Must Know",
            "title_ko": "SAT 필수 어휘 100개",
            "date": "2026-04-15",
            "content": "top_100_sat_words",
            "meta_desc": "Boost your SAT verbal score with the 100 highest-frequency vocabulary words. Definitions, example sentences, and proven memory techniques for fast retention.",
            "meta_desc_ko": "SAT 버벌 점수를 높여주는 고빈출 어휘 100개. 정의, 예문, 그리고 빠른 암기를 위한 검증된 기억법.",
            "related": ["ielts-essential-words", "business-english-vocabulary", "word-roots-prefixes-suffixes"]
        },
        "ielts-essential-words": {
            "title": "50 Essential IELTS Words to Improve Your Band Score",
            "date": "2026-04-10",
            "content": "ielts_essential_words",
            "meta_desc": "Master 50 essential IELTS vocabulary words to lift your writing and speaking band score. Definitions, example sentences, and natural usage in academic English.",
            "related": ["top-100-sat-words", "business-english-vocabulary", "vocabulary-habit-building"]
        },
        "word-game-tips": {
            "title": "10 Best Strategies to Win Word Games Every Time",
            "date": "2026-03-01",
            "content": "wordle_tips",
            "title_ko": "단어 게임 승리 전략 10가지",
            "meta_desc": "10 expert strategies to consistently win word guessing games. Best starting words, letter frequency tactics, double-letter detection, and elimination tricks.",
            "meta_desc_ko": "단어 추측 게임에서 일관되게 이기는 10가지 전문 전략. 최고의 시작 단어, 글자 빈도 활용법, 중복 글자 탐지, 그리고 제거법.",
            "related": ["best-starting-words", "pattern-recognition-word-games", "word-game-history"]
        },
        "best-starting-words": {
            "title": "The Best Starting Words for Word Games in 2026",
            "date": "2026-02-20",
            "content": "best_starting_words",
            "title_ko": "2026년 단어 게임 최고의 시작 단어",
            "meta_desc": "Discover the top 20 starting words for word puzzle games in 2026. CRANE, STARE, AUDIO ranked by letter coverage. Solve faster with the best opener for you.",
            "meta_desc_ko": "2026년 단어 퍼즐 최고의 시작 단어 20개. CRANE, STARE, AUDIO를 글자 커버리지 기준으로 순위 매김. 본인에게 맞는 최고의 시작 단어로 더 빨리 풀어보세요.",
            "related": ["word-game-tips", "common-5-letter-words", "pattern-recognition-word-games"]
        },
        "word-game-history": {
            "title": "The History of Word Guessing Games",
            "date": "2026-02-10",
            "content": "word_game_history",
            "meta_desc": "From 1913 crosswords to Scrabble, Boggle, and modern viral daily puzzles — a century of design that shaped today's word game culture and global appeal.",
            "related": ["science-of-word-games", "word-games-children-reading", "reading-comprehension-word-games"]
        },
        "daily-habits-vocabulary": {
            "title": "5 Daily Habits That Will Rapidly Expand Your Vocabulary",
            "date": "2026-04-25",
            "content": "daily_habits_vocabulary",
            "meta_desc": "5 research-backed daily habits to expand your vocabulary fast. The simple 10-minute routine that beats cramming, plus how to make new words actually stick.",
            "related": ["vocabulary-habit-building", "word-roots-prefixes-suffixes", "word-games-children-reading"]
        },
        "science-of-word-games": {
            "title": "The Science Behind Word Games: How Puzzles Boost Your Brain",
            "date": "2026-04-22",
            "content": "science_of_word_games",
            "meta_desc": "The neuroscience of word games: how daily puzzles boost memory, attention, and verbal fluency. Research-backed evidence for brain benefits at any age.",
            "related": ["reading-comprehension-word-games", "word-games-children-reading", "word-game-history"]
        },
        "common-5-letter-words": {
            "title": "The 50 Most Common 5-Letter Words in English (And How to Use Them)",
            "date": "2026-05-03",
            "content": "common_5_letter_words",
            "meta_desc": "The 50 most common 5-letter English words ranked by frequency. Definitions, usage examples, and how knowing these words improves daily word game performance.",
            "related": ["best-starting-words", "word-game-tips", "word-roots-prefixes-suffixes"]
        },
        "word-roots-prefixes-suffixes": {
            "title": "Word Roots, Prefixes and Suffixes: The Ultimate Vocabulary Cheat Sheet",
            "date": "2026-04-30",
            "content": "word_roots_prefixes_suffixes",
            "meta_desc": "30 essential Latin and Greek roots, prefixes, and suffixes that unlock thousands of English words. Learn one root, gain 20 words. Vocabulary multiplier guide.",
            "related": ["greek-latin-roots-english", "vocabulary-habit-building", "top-100-sat-words"]
        },
        "vocabulary-habit-building": {
            "title": "How to Build a Vocabulary Habit That Actually Sticks",
            "date": "2026-04-27",
            "content": "vocabulary_habit_building",
            "meta_desc": "How to build a vocabulary habit that survives past week one. Behavioral science principles for lasting word learning, plus daily and weekly routine templates.",
            "related": ["daily-habits-vocabulary", "word-roots-prefixes-suffixes", "ielts-essential-words"]
        },
        "reading-comprehension-word-games": {
            "title": "How Word Games Improve Reading Comprehension",
            "date": "2026-04-03",
            "content": "reading_comprehension_word_games",
            "meta_desc": "Research shows daily word games measurably improve reading comprehension, vocabulary recall, and verbal IQ. Here's the cognitive science and how to apply it.",
            "related": ["science-of-word-games", "word-games-children-reading", "vocabulary-habit-building"]
        },
        "greek-latin-roots-english": {
            "title": "Greek and Latin Roots Every English Learner Should Know",
            "date": "2026-03-28",
            "content": "greek_latin_roots_english",
            "meta_desc": "25 classical Greek and Latin roots that appear in thousands of English words. Definitions, modern examples, and how knowing roots accelerates vocabulary growth.",
            "related": ["word-roots-prefixes-suffixes", "top-100-sat-words", "business-english-vocabulary"]
        },
        "pattern-recognition-word-games": {
            "title": "Pattern Recognition: The Hidden Skill That Wins Word Puzzles",
            "date": "2026-03-20",
            "content": "pattern_recognition_word_games",
            "meta_desc": "Pattern recognition separates expert word puzzle solvers from beginners. Learn how to train this hidden skill with practical drills and daily exercises.",
            "related": ["word-game-tips", "best-starting-words", "science-of-word-games"]
        },
        "business-english-vocabulary": {
            "title": "40 Essential Business English Words You Need at Work",
            "date": "2026-02-15",
            "content": "business_english_vocabulary",
            "meta_desc": "40 essential business English vocabulary words to sound confident in meetings, emails, and presentations. Definitions, real examples, and natural usage tips.",
            "related": ["top-100-sat-words", "ielts-essential-words", "vocabulary-habit-building"]
        },
        "word-games-children-reading": {
            "title": "How Word Games Help Children Learn to Read",
            "date": "2026-02-12",
            "content": "word_games_children_reading",
            "meta_desc": "Research-backed evidence on how word games accelerate phonics, spelling, and reading fluency in children. Age-by-age guidance for parents and educators.",
            "related": ["reading-comprehension-word-games", "science-of-word-games", "daily-habits-vocabulary"]
        },
    }
    post = posts.get(slug)
    if not post:
        return render_template("404.html"), 404

    # Attach tag for the badge shown next to the post title
    post["tag"] = BLOG_TAGS.get(slug, "vocab")

    # Resolve related slugs to title+url for template (prefer KO title when available)
    lang = session.get("lang", "en")
    related_posts = []
    for s in post.get("related", []):
        if s in posts:
            other = posts[s]
            other_title = other.get("title_ko") if lang == "ko" and other.get("title_ko") else other["title"]
            related_posts.append({"slug": s, "title": other_title, "url": f"/blog/{s}"})

    # Pick title/meta in the current language with a clean fallback to English
    page_title = post.get("title_ko") if lang == "ko" and post.get("title_ko") else post["title"]
    page_meta  = post.get("meta_desc_ko") if lang == "ko" and post.get("meta_desc_ko") else post.get("meta_desc", f"Read: {post['title']}")

    return render_template("blog/post.html",
        title=f"{page_title} — WordMaster Blog",
        meta_desc=page_meta,
        post=post, slug=slug,
        related_posts=related_posts)

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
    elif mode == "news":
        articles = fetch_news_articles()
        word, _ = pick_news_word(articles)
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

@app.route("/news-challenge")
def news_challenge():
    return render_template("news_challenge.html",
        title="News Word Challenge — WordMaster | Vocabulary from BBC Headlines",
        meta_desc="Read today's BBC World News headlines, then guess the hidden 5-letter word. Learn real-world vocabulary in context. Updated daily. Free word game with news.",
        mode="news", word_length=5, max_guesses=6)

@app.route("/api/news-articles")
def api_news_articles():
    articles = fetch_news_articles()
    _, word_source = pick_news_word(articles)
    return jsonify({"articles": articles, "wordSource": word_source})

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

    # Core static pages
    static_urls = [
        "/", "/daily", "/unlimited", "/easy", "/hard",
        "/leaderboard", "/how-to-play", "/about",
        "/contact", "/faq", "/privacy", "/terms",
        "/news-challenge", "/archive",
        # Learning-level Tile Guess routes
        "/middle", "/high", "/college", "/custom",
        # Themed Tile Guess routes
        "/category/animals", "/category/food",
        # Learning data pages
        "/my-words", "/my-weak-words", "/my-progress",
    ]

    # Alternate puzzle formats — same vocabulary sources rendered as Anagram / Hangman
    _puzzle_categories = ["middle", "high", "college", "custom", "news",
                          "animals", "food", "easy", "hard"]
    puzzle_urls = ["/anagram", "/hangman"]
    for cat in _puzzle_categories:
        puzzle_urls.append(f"/anagram/{cat}")
        puzzle_urls.append(f"/hangman/{cat}")

    # Blog index + individual posts
    blog_urls = [
        "/blog",
        "/blog/anagram-strategy",
        "/blog/hangman-letter-frequency",
        "/blog/three-puzzle-formats",
        "/blog/word-game-tips", "/blog/best-starting-words", "/blog/word-game-history",
        "/blog/top-100-sat-words", "/blog/ielts-essential-words",
        "/blog/daily-habits-vocabulary", "/blog/science-of-word-games",
        "/blog/common-5-letter-words", "/blog/word-roots-prefixes-suffixes",
        "/blog/vocabulary-habit-building", "/blog/reading-comprehension-word-games",
        "/blog/greek-latin-roots-english", "/blog/pattern-recognition-word-games",
        "/blog/business-english-vocabulary", "/blog/word-games-children-reading",
    ]

    # /word-of-day was retired — do not list (it 301-redirects to /daily and
    # redirect URLs in a sitemap are flagged as low-quality signals by Google).

    urls = static_urls + puzzle_urls + blog_urls

    today_str = date.today().isoformat()
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml_lines.append(
            f"  <url><loc>{base}{u}</loc>"
            f"<lastmod>{today_str}</lastmod></url>"
        )
    xml_lines.append("</urlset>")
    return Response("\n".join(xml_lines), mimetype="application/xml")

@app.route("/robots.txt")
def robots():
    txt = "User-agent: *\nAllow: /\nSitemap: https://wordmaster.store/sitemap.xml\n"
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
