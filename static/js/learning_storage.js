// Shared learning data storage — used by anagram.js and hangman.js
// Writes to the same wm_vocab localStorage key that wordle (game.js) uses,
// so all puzzle formats feed the same My Words / Weak Words / Progress views.

(function () {
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
