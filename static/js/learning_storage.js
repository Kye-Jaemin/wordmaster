// Shared learning data storage + Word Learning Card population — used by all
// puzzle formats so the post-game UI looks identical regardless of which game
// the user just finished. Writes to the same wm_vocab localStorage key as
// game.js so My Words / Weak Words / Progress aggregate across all formats.

(function () {
  // ── Word Learning Card population ───────────────────────────────────────
  // Fetches the full dictionary entry from /api/word-info and fills in the
  // word-learning-card DOM elements that anagram_game.html, hangman_game.html
  // and index.html all share.
  window.wmPopulateLearningCard = async function (word) {
    if (!word) return;
    const card    = document.getElementById("word-learning-card");
    const loading = document.getElementById("definition-loading");
    if (!card) return;
    if (loading) loading.classList.remove("d-none");
    try {
      const res  = await fetch(`/api/word-info?word=${word.toLowerCase()}`);
      const data = await res.json();
      if (loading) loading.classList.add("d-none");
      if (!data || !data.meanings || data.meanings.length === 0) return;

      const learnWord = document.getElementById("learn-word");
      const learnPho  = document.getElementById("learn-phonetic");
      if (learnWord) learnWord.textContent = data.word || word.toUpperCase();
      if (learnPho)  learnPho.textContent  = data.phonetic || "";

      const meaningsEl = document.getElementById("learn-meanings");
      if (meaningsEl) {
        meaningsEl.innerHTML = "";
        data.meanings.slice(0, 2).forEach(m => {
          const posEl = document.createElement("span");
          posEl.className = "badge bg-secondary me-1 mb-1";
          posEl.textContent = m.partOfSpeech;
          meaningsEl.appendChild(posEl);
          (m.definitions || []).slice(0, 2).forEach(d => {
            const defP = document.createElement("p");
            defP.className = "mb-1 small";
            defP.innerHTML = `<i class="bi bi-dot text-primary"></i>${d.definition}`;
            meaningsEl.appendChild(defP);
            if (d.example) {
              const exP = document.createElement("p");
              exP.className = "text-muted fst-italic small ms-3 mb-1";
              exP.textContent = `"${d.example}"`;
              meaningsEl.appendChild(exP);
            }
          });
        });
      }

      const synWrap = document.getElementById("learn-synonyms-wrap");
      const antWrap = document.getElementById("learn-antonyms-wrap");
      const synEl   = document.getElementById("learn-synonyms");
      const antEl   = document.getElementById("learn-antonyms");
      const synant  = document.getElementById("learn-synant");
      if (synEl && data.synonyms && data.synonyms.length) {
        synEl.textContent = data.synonyms.join(", ");
        if (synWrap) synWrap.classList.remove("d-none");
        if (synant)  synant.classList.remove("d-none");
      }
      if (antEl && data.antonyms && data.antonyms.length) {
        antEl.textContent = data.antonyms.join(", ");
        if (antWrap) antWrap.classList.remove("d-none");
        if (synant)  synant.classList.remove("d-none");
      }

      if (data.origin) {
        const etym   = document.getElementById("learn-etymology");
        const origin = document.getElementById("learn-origin");
        if (origin) origin.textContent = data.origin;
        if (etym)   etym.classList.remove("d-none");
      }

      card.classList.remove("d-none");
    } catch (e) {
      if (loading) loading.classList.add("d-none");
    }
  };

  // Show the post-game AdSense result block (300×250) if it's present in the DOM.
  window.wmShowResultAd = function () {
    const ad = document.getElementById("result-ad");
    if (ad) ad.classList.remove("d-none");
  };

  // ── Initial meaning clue ────────────────────────────────────────────────
  // Anagram and Hangman start with no semantic clue — just scrambled tiles or
  // blanks — which makes harder words almost unguessable. This fetches a
  // spoiler-safe definition from /api/hint and renders it into #clue-panel /
  // #clue-content at round start. The answer (and simple inflections) is masked
  // so the clue hints at meaning without handing over the word.
  function maskAnswer(text, word) {
    if (!text || !word) return text || "";
    const esc = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re  = new RegExp("\\b" + esc + "(?:s|es|ed|ing|d)?\\b", "gi");
    return text.replace(re, "•".repeat(Math.max(3, word.length)));
  }

  window.wmShowClue = async function (word) {
    const panel   = document.getElementById("clue-panel");
    const content = document.getElementById("clue-content");
    const loading = document.getElementById("clue-loading");
    if (!panel || !content || !word) return;
    const ko = (window.WM_LANG === "ko");
    panel.classList.add("d-none");
    content.innerHTML = "";
    if (loading) loading.classList.remove("d-none");
    try {
      const res  = await fetch(`/api/hint?word=${word.toLowerCase()}`);
      const data = await res.json();
      if (loading) loading.classList.add("d-none");
      const def = maskAnswer(data.definition || "", word);
      if (!def) return;
      let html = `<strong><i class="bi bi-lightbulb-fill me-1 text-warning"></i>${ko ? "힌트" : "Clue"}</strong>`;
      if (data.partOfSpeech) html += ` <em class="text-muted">(${data.partOfSpeech})</em>`;
      html += `<br>${def}`;
      if (data.example) html += `<br><small class="text-muted fst-italic">${ko ? "예: " : "e.g. "}"${maskAnswer(data.example, word)}"</small>`;
      content.innerHTML = html;
      panel.classList.remove("d-none");
    } catch (e) {
      if (loading) loading.classList.add("d-none");
    }
  };

  // ── Rewarded-ad gate for extra hints ────────────────────────────────────
  // Builds a one-off "advertisement" overlay containing the site's existing
  // 300×250 AdSense unit plus a short countdown. When the countdown ends the
  // Claim button activates and, on click, invokes onReward() — a rewarded-video
  // style flow built on the display inventory the site already runs.
  window.wmWatchAdForReward = function (onReward) {
    const ko = (window.WM_LANG === "ko");
    const COUNTDOWN = 5;

    const ov = document.createElement("div");
    ov.className = "wm-ad-overlay";
    ov.style.cssText = "position:fixed;inset:0;z-index:1090;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;padding:16px;";
    ov.innerHTML =
      '<div style="background:#fff;border-radius:12px;max-width:360px;width:100%;padding:18px 18px 12px;text-align:center;box-shadow:0 12px 44px rgba(0,0,0,.35)">' +
        '<div class="text-muted mb-2" style="font-size:.7rem;text-transform:uppercase;letter-spacing:.06em">' + (ko ? "광고" : "Advertisement") + '</div>' +
        '<div style="min-height:250px;display:flex;align-items:center;justify-content:center;background:#f6f7f9;border-radius:8px;overflow:hidden">' +
          '<ins class="adsbygoogle" style="display:inline-block;width:300px;height:250px" data-ad-client="ca-pub-3911396624649383" data-ad-slot="9633203230"></ins>' +
        '</div>' +
        '<button class="wm-ad-claim btn btn-primary w-100 mt-3" disabled><i class="bi bi-hourglass-split me-1"></i><span class="wm-ad-count">' + COUNTDOWN + '</span></button>' +
        '<button class="wm-ad-cancel btn btn-sm btn-link text-muted mt-1 text-decoration-none">' + (ko ? "닫기" : "Close") + '</button>' +
      '</div>';
    document.body.appendChild(ov);
    try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (e) {}

    const claimBtn = ov.querySelector(".wm-ad-claim");
    const cancelBtn = ov.querySelector(".wm-ad-cancel");
    const countEl  = ov.querySelector(".wm-ad-count");
    let left = COUNTDOWN;
    const timer = setInterval(() => {
      left--;
      if (left > 0) {
        if (countEl) countEl.textContent = left;
      } else {
        clearInterval(timer);
        claimBtn.disabled = false;
        claimBtn.innerHTML = '<i class="bi bi-unlock-fill me-1"></i>' + (ko ? "힌트 받기" : "Claim hint");
      }
    }, 1000);

    function close() {
      clearInterval(timer);
      if (ov.parentNode) ov.parentNode.removeChild(ov);
    }
    claimBtn.addEventListener("click", () => {
      if (claimBtn.disabled) return;
      close();
      if (typeof onReward === "function") onReward();
    });
    cancelBtn.addEventListener("click", close);
    ov.addEventListener("click", (e) => { if (e.target === ov) close(); });
  };


  window.wmSaveVocab = function (word, won, scoreNumber, gameMode) {
    if (!word) return;
    word = word.toUpperCase();
    const today = new Date().toISOString().slice(0, 10);

    const defaults = {
      words: {},
      weak_words: [],
      daily: {},
      streak: { current: 0, longest: 0, last_daily: null },
    };
    const v = JSON.parse(localStorage.getItem("wm_vocab") || JSON.stringify(defaults));
    v.words = v.words || {};
    v.weak_words = v.weak_words || [];
    v.daily = v.daily || {};
    v.streak = v.streak || { current: 0, longest: 0, last_daily: null };

    const isNew = !v.words[word];
    if (isNew) {
      v.words[word] = { first_seen: today, last_seen: today, play_count: 0, won_count: 0, best_guess: null };
    }
    const w = v.words[word];
    w.last_seen = today;
    w.play_count = (w.play_count || 0) + 1;
    if (won) {
      w.won_count = (w.won_count || 0) + 1;
      // best_guess is wordle-specific (fewest guesses); leave it null for other puzzles
      if (gameMode === "wordle" || gameMode === "daily_wordle") {
        if (w.best_guess === null || w.best_guess === undefined || scoreNumber < w.best_guess) {
          w.best_guess = scoreNumber;
        }
      }
    }

    const idx = v.weak_words.indexOf(word);
    if (!won && idx === -1) v.weak_words.push(word);
    else if (won && idx !== -1) v.weak_words.splice(idx, 1);

    if (!v.daily[today]) v.daily[today] = { games: 0, wins: 0, new_words: 0 };
    v.daily[today].games++;
    if (won) v.daily[today].wins++;
    if (isNew) v.daily[today].new_words++;

    // Streak only counts daily wordle
    if (gameMode === "daily_wordle") {
      if (won) {
        const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
        if (v.streak.last_daily === yesterday) v.streak.current = (v.streak.current || 0) + 1;
        else if (v.streak.last_daily !== today) v.streak.current = 1;
        if (v.streak.current > (v.streak.longest || 0)) v.streak.longest = v.streak.current;
        v.streak.last_daily = today;
      } else {
        v.streak.current = 0;
        v.streak.last_daily = today;
      }
    }

    localStorage.setItem("wm_vocab", JSON.stringify(v));
  };
})();
