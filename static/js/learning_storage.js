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

  // Shared share-result for the grid-less formats (Anagram, Hangman). The Tile
  // game keeps its own emoji-grid shareResult in game.js; this builds a spoiler-
  // free text line + the daily streak + a "come back tomorrow" CTA, so all three
  // formats can share and feed the same viral loop.
  window.wmShareResult = function (opts) {
    // opts: { label: "Anagram"/"애너그램", detail: "Solved in 2 tries" }
    const ko = (window.WM_LANG === "ko");
    let text = "WordMaster " + (opts.label || "");
    try {
      const v = JSON.parse(localStorage.getItem("wm_vocab") || "{}");
      const days = v.streak && v.streak.current;
      if (days && days >= 2) text += "  " + (ko ? ("🔥 " + days + "일 연속") : ("🔥 " + days + "-day streak"));
    } catch (e) { /* ignore malformed storage */ }
    if (opts.detail) text += "\n" + opts.detail;
    text += "\n\n" + (ko ? "내일 또 만나요 👉" : "Come back tomorrow 👉") + " https://wordmaster.store";
    const done = function () {
      const ta = document.getElementById("toast-area");
      if (ta) {
        ta.innerHTML = '<span class="badge bg-success">' + (ko ? "복사됨!" : "Copied!") + '</span>';
        setTimeout(function () { ta.innerHTML = ""; }, 2000);
      }
    };
    if (navigator.clipboard) { navigator.clipboard.writeText(text).then(done, function () { window.prompt("Copy:", text); }); }
    else { window.prompt("Copy your result:", text); }
    return text;
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
    let v;
    try { v = JSON.parse(localStorage.getItem("wm_vocab") || JSON.stringify(defaults)); }
    catch (e) { v = JSON.parse(JSON.stringify(defaults)); }  // corrupt storage -> reset
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
