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
